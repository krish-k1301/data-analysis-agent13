"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import "./globals.css";

const navItems = [
  { href: "/", label: "Dashboard", icon: "■" },
  { href: "/datasets", label: "Datasets", icon: "◆" },
  { href: "/findings", label: "Findings", icon: "▶" },
  { href: "/review", label: "Review Queue", icon: "◈" },
];

function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>Audit Agent</h1>
        <div className="subtitle">Data Analysis Platform</div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={isActive(item.href) ? "active" : ""}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-footer">v1.0.0 MVP</div>
    </aside>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>Audit Agent — Data Analysis Platform</title>
        <meta
          name="description"
          content="Agentic AI data analysis agent for audit and risk assessment. Upload datasets, detect anomalies, score risk, and review findings."
        />
      </head>
      <body>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
