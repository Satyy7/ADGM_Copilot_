"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FileSearch,
  FileText,
  BarChart3,
  Gavel,
  LayoutDashboard,
  Landmark,
  ChevronRight,
} from "lucide-react";

const NAV = [
  { href: "/",          icon: LayoutDashboard, label: "Dashboard",        desc: "Overview" },
  { href: "/chat",      icon: MessageSquare,   label: "AI Copilot",       desc: "Ask anything" },
  { href: "/review",    icon: FileSearch,      label: "Document Review",  desc: "Compliance check" },
  { href: "/clauses",   icon: FileText,        label: "Clause Generator", desc: "Draft clauses" },
  { href: "/analytics", icon: BarChart3,       label: "Analytics",        desc: "Insights & SQL" },
  { href: "/cases",     icon: Gavel,           label: "Case Search",      desc: "Legal precedents" },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside
      style={{ width: "var(--sidebar-w)", minWidth: "var(--sidebar-w)" }}
      className="h-screen sticky top-0 flex flex-col bg-white border-r border-[var(--border)] z-30 overflow-hidden"
    >
      {/* Logo */}
      <div className="px-5 pt-6 pb-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg,#D97706 0%,#92400E 100%)" }}
          >
            <Landmark size={17} className="text-white" />
          </div>
          <div>
            <p className="font-display font-bold text-sm text-[var(--text)] leading-tight">ADGM</p>
            <p className="text-[10px] font-semibold text-[var(--text-3)] tracking-wide uppercase leading-none mt-0.5">
              Compliance Copilot
            </p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        <p className="section-label px-2 mb-3">Navigation</p>
        {NAV.map(({ href, icon: Icon, label, desc }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 group",
                active
                  ? "bg-amber-50 border border-amber-200 text-amber-800"
                  : "border border-transparent hover:bg-warm-50 text-[var(--text-2)] hover:text-[var(--text)]",
              ].join(" ")}
            >
              <div
                className={[
                  "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-150",
                  active
                    ? "bg-amber-100 text-amber-700"
                    : "bg-warm-100 text-[var(--text-3)] group-hover:bg-amber-50 group-hover:text-amber-600",
                ].join(" ")}
              >
                <Icon size={15} />
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-[13px] font-medium leading-tight truncate ${active ? "text-amber-800" : ""}`}>
                  {label}
                </p>
                <p className={`text-[10.5px] leading-tight truncate mt-0.5 ${active ? "text-amber-500" : "text-[var(--text-3)]"}`}>
                  {desc}
                </p>
              </div>
              {active && <ChevronRight size={12} className="text-amber-400 flex-shrink-0" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer status */}
      <div className="px-4 py-4 border-t border-[var(--border)]">
        <div className="bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5">
          <div className="flex items-center gap-2 mb-1.5">
            <div className="status-dot" />
            <p className="text-[11px] font-semibold text-amber-800">All Systems Online</p>
          </div>
          <p className="text-[10px] text-amber-600 leading-relaxed">
            All services operational
          </p>
        </div>
      </div>
    </aside>
  );
}
