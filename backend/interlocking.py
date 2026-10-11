"""Station platform assignment, departure signals and locked switch routes."""
class StationInterlocking:
    def __init__(self, simulator, station, platforms=4):
        self.simulator = simulator
        self.station = station
        self.platforms = platforms
        self.assignments = {}
        self.stopped_signals = set()
        simulator.interlocking = self
        self.sync()

    def sync(self):
        sim = self.simulator
        for tid in list(self.assignments):
            train = sim.trains[tid]
            if train.current_station != self.station or train.status == 'ARRIVED':
                del self.assignments[tid]
        for train in sim.trains.values():
            if train.current_station != self.station or train.status == 'ARRIVED':
                continue
            if train.train_id not in self.assignments:
                used = set(self.assignments.values())
                available = next((p for p in range(1, self.platforms + 1) if p not in used), None)
                if available is not None:
                    self.assignments[train.train_id] = available

    def blocked_reason(self, train_id):
        self.sync()
        train = self.simulator.trains[train_id]
        if train.current_station != self.station:
            return None
        platform = self.assignments.get(train_id)
        if platform is None:
            return 'Waiting outside the station for a free platform.'
        if platform in self.stopped_signals:
            return f'Platform {platform} departure signal is held at red.'
        if self.simulator.current_time_min + 1e-8 < self.throat_release_time():
            return 'Station exit switch is occupied. Wait for the departing train to clear it.'
        return None

    def throat_release_time(self):
        departures = [e['time_min'] for e in self.simulator.history
                      if e['event'] == 'SECTION_ENTERED' and e.get('from_station') == self.station]
        return max(departures) + 1.0 if departures else 0.0

    def change_platform(self, train_id, platform):
        self.sync()
        train = self.simulator.trains.get(train_id)
        if train is None or train.current_station != self.station or train.status not in {'WAITING', 'APPROACHING', 'NOT_ENTERED'}:
            raise ValueError('Only a waiting train at this station can change platform.')
        if type(platform) is not int or not 1 <= platform <= self.platforms:
            raise ValueError('Choose a valid platform.')
        if platform in self.assignments.values() and self.assignments.get(train_id) != platform:
            raise ValueError('That platform is occupied or route-locked.')
        old = self.assignments.get(train_id)
        self.assignments[train_id] = platform
        self.simulator.log_event('PLATFORM_CHANGED', train_id=train_id, from_platform=old, to_platform=platform)

    def set_signal(self, platform, stop):
        if type(platform) is not int or not 1 <= platform <= self.platforms or type(stop) is not bool:
            raise ValueError('Invalid signal command.')
        occupant = next((tid for tid, p in self.assignments.items() if p == platform), None)
        if occupant and self.simulator.trains[occupant].status == 'RUNNING':
            raise ValueError('Departure route is locked until its train clears the section.')
        if stop:
            self.stopped_signals.add(platform)
        else:
            self.stopped_signals.discard(platform)
        self.simulator.log_event('SIGNAL_HELD' if stop else 'SIGNAL_AUTOMATIC', platform=platform)

    def snapshot(self):
        self.sync()
        result = []
        for platform in range(1, self.platforms + 1):
            tid = next((tid for tid, p in self.assignments.items() if p == platform), None)
            train = self.simulator.trains.get(tid)
            route, destination = None, None
            reason = 'No train assigned.'
            aspect = 'RED'
            locked = bool(train and train.status == 'RUNNING')
            if train:
                movement = self.simulator.movement_model.build_movement(tid)
                if train.section_index < len(movement.section_sequence):
                    route = movement.section_sequence[train.section_index]
                    section = self.simulator.network.get_section(route)
                    destination = section.to_station if section.from_station == self.station else section.from_station
                if locked:
                    reason = 'Route locked: train is clearing the outgoing section.'
                elif platform in self.stopped_signals:
                    reason = 'Signal manually held at red.'
                elif self.simulator.current_time_min < max(train.entry_time_min, train.ready_time_min):
                    reason = 'Train is not ready to depart.'
                elif self.blocked_reason(tid):
                    reason = self.blocked_reason(tid)
                elif route:
                    conflict = self.simulator._conflict_detector.check_section_conflict(tid, route)
                    if conflict['conflict']:
                        reason = conflict['reason']
                    else:
                        aspect, reason = 'GREEN', 'Route clear. Safe to dispatch.'
            result.append({'platform': platform, 'train_id': tid, 'aspect': aspect,
                           'held': platform in self.stopped_signals, 'locked': locked,
                           'section': route, 'destination': destination, 'reason': reason})
        return {'platforms': result, 'assignments': dict(self.assignments),
                'outside': [t.train_id for t in self.simulator.trains.values()
                            if t.current_station == self.station and t.status != 'ARRIVED' and t.train_id not in self.assignments]}
