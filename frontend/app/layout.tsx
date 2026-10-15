import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Railwise — Railway intelligence', description: 'A visual control room for AI railway traffic simulation.' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) {
  // Translation extensions can add attributes to html before React hydrates.
  return <html lang="en" suppressHydrationWarning><body>{children}</body></html>;
}
