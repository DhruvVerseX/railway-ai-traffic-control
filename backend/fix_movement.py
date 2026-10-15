from pathlib import Path
p=Path('simulation/simulator.py')
s=p.read_text()
s=s.replace('    remaining_time_min: float = 0.0','    remaining_time_min: float = 0.0\n    waiting_time_min: float = 0.0\n    ready_time_min: float = 0.0')
s=s.replace('        self.trains = {}','        self.trains = {}\n        self.dispatch_at_stations = False',1)
s=s.replace('        # Create movement model\n', '''        if self.current_time_min < train.ready_time_min - 1e-9:
            return False

        # Create movement model
''',1)
a=s.index('        # Check whether section is occupied',s.index('    def start_train'))
b=s.index('        from_station, to_station',a)
s=s[:a]+'''        if self._conflict_detector is not None:
            conflict = self._conflict_detector.check_section_conflict(train_id, section_id)
            if conflict['conflict']:
                self.set_train_waiting(train_id, reason=conflict['reason'], section_id=section_id)
                return False
        elif section_id in self.section_occupancy:
            self.set_train_waiting(train_id, reason='Section occupied', section_id=section_id)
            return False

'''+s[b:]
a=s.index('        # Determine movement direction',s.index('    def start_train'))
b=s.index('        # If train was previously waiting',a)
s=s[:a]+'''        # The route's actual station is authoritative, including branch routes.
        if train.current_station == from_station:
            train.next_station = to_station
        elif train.current_station == to_station:
            train.next_station = from_station
        else:
            raise ValueError(f'Train {train_id} is not at an endpoint of {section_id}')

'''+s[b:]
s=s.replace('''                    if train.status == "RUNNING":

                        train.remaining_time_min -= elapsed''','''                    if train.status in {'WAITING', 'NOT_ENTERED', 'APPROACHING'}:
                        eligible_time = max(self.current_time_min, train.entry_time_min, train.ready_time_min)
                        waited = max(0.0, next_event_time - eligible_time)
                        train.waiting_time_min += waited
                        train.delay_min += waited
                    if train.status == "RUNNING":

                        train.remaining_time_min -= elapsed''')
a=s.index('    def complete_current_section(')
b=s.index('    # ---------------------------------------------------------\n    # LOAD TRAFFIC',a)
s=s[:a]+'''    def complete_current_section(self, train_id):
        train = self.get_train_state(train_id)
        section_id = train.current_section
        if section_id is None:
            return False
        if self.section_occupancy.get(section_id) == train_id:
            del self.section_occupancy[section_id]
            if self._conflict_detector is not None:
                self._conflict_detector.record_section_exit(section_id)
        train.current_station = train.next_station
        train.current_section = None
        train.next_station = None
        train.remaining_time_min = 0.0
        train.section_index += 1
        self.log_event('SECTION_COMPLETED', train_id=train_id, section_id=section_id,
                       station_id=train.current_station)
        movement = self.movement_model.build_movement(train_id)
        if train.section_index >= len(movement.section_sequence):
            train.status = 'ARRIVED'
            self.log_event('TRAIN_ARRIVED', train_id=train_id, station_id=train.current_station)
            return True
        record = self.movement_model.train_database.get_train(train_id)
        dwell = float(record.get('dwell_min', 0)) if self.dispatch_at_stations and str(record.get('stops_intermediate')).lower() == 'true' else 0.0
        train.ready_time_min = self.current_time_min + dwell
        self.set_train_waiting(train_id, reason='Reached next station',
                               section_id=movement.section_sequence[train.section_index])
        if not self.dispatch_at_stations:
            return self.start_train(train_id)
        return True

'''+s[b:]
# Infer the next section from station location for loaded intermediate trains.
s=s.replace('''                sim_train.section_index = 0

            # Register existing section occupancy''','''                cursor = train_record['entry_station']
                sim_train.section_index = len(movement.section_sequence)
                for index, sid in enumerate(movement.section_sequence):
                    if cursor == sim_train.current_station:
                        sim_train.section_index = index
                        break
                    section = self.network.get_section(sid)
                    cursor = section.to_station if cursor == section.from_station else section.from_station
                if sim_train.section_index == len(movement.section_sequence) and sim_train.status != 'ARRIVED':
                    raise ValueError(f'Invalid station for {sim_train.train_id}')

            # Register existing section occupancy''')
s=s.replace('''            # Register existing section occupancy
''','''            if sim_train.status == 'RUNNING':
                section = self.network.get_section(sim_train.current_section)
                sim_train.remaining_time_min = section.travel_time(float(train_record['max_speed_kmph']))

            # Register existing section occupancy
''')
p.write_text(s)
