import "./globals.css";

export const metadata = {
  title: "Agentic Stock Dashboard",
  description: "Autonomous multi-agent stock analysis dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <div className="fixed inset-0 -z-10 bg-gradient-to-br from-slate-950 via-slate-900 to-black" />
        <div className="fixed left-1/2 top-1/3 -z-10 h-72 w-72 -translate-x-1/2 rounded-full bg-emerald-500/10 blur-[120px]" />
        {children}
      </body>
    </html>
  );
}
