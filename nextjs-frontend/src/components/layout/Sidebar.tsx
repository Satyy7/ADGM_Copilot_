"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, FileSearch, Wand2, BarChart3,
  FolderSearch, Home, ChevronLeft, ChevronRight,
  Shield, Cpu,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/",          label: "Dashboard",        icon: Home,          color: "#d4a030" },
  { href: "/chat",      label: "Compliance Chat",  icon: MessageSquare, color: "#34d4a0" },
  { href: "/review",    label: "Document Review",  icon: FileSearch,    color: "#7dd3fc" },
  { href: "/clauses",   label: "Clause Generator", icon: Wand2,         color: "#c084fc" },
  { href: "/analytics", label: "Analytics",        icon: BarChart3,     color: "#fb923c" },
  { href: "/cases",     label: "Similar Cases",    icon: FolderSearch,  color: "#f472b6" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="relative flex-shrink-0 flex flex-col h-screen bg-navy-900 border-r border-gold-500/10 overflow-hidden"
      style={{ minWidth: collapsed ? 64 : 240 }}
    >
      {/* Gold top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gold-500/60 to-transparent" />

      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/5">
        <div className="relative flex-shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gold-400/20 to-gold-600/10 border border-gold-500/30 flex items-center justify-center">
            <Shield className="w-5 h-5 text-gold-400" />
          </div>
          <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-jade-400 border-2 border-navy-900" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <p className="text-sm font-bold text-gold-gradient leading-none">ADGM</p>
              <p className="text-xs text-slate-400 mt-0.5 whitespace-nowrap">Compliance Copilot</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto overflow-x-hidden">
        {NAV.map(({ href, label, icon: Icon, color }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "relative flex items-center gap-3 rounded-xl px-3 py-2.5 cursor-pointer transition-all duration-200 group",
                  active
                    ? "bg-gold-500/10 border border-gold-500/20"
                    : "hover:bg-white/5 border border-transparent"
                )}
              >
                {/* Active indicator */}
                {active && (
                  <motion.div
                    layoutId="active-pill"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                    style={{ background: color }}
                  />
                )}

                <Icon
                  className="flex-shrink-0 transition-transform duration-200 group-hover:scale-110"
                  size={18}
                  style={{ color: active ? color : "#6b7ea8" }}
                />

                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className={cn(
                        "text-sm font-medium whitespace-nowrap",
                        active ? "text-white" : "text-slate-400 group-hover:text-slate-200"
                      )}
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="px-2 pb-4 border-t border-white/5 pt-3">
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="glass rounded-xl px-3 py-2.5 mb-3"
            >
              <div className="flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-jade-400 flex-shrink-0" />
                <span className="text-xs text-slate-400">AI Engine</span>
                <span className="ml-auto text-xs text-jade-400 font-medium">Online</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <div className="status-dot w-1.5 h-1.5 flex-shrink-0" />
                <span className="text-xs text-slate-500">Gemini 2.5 Flash</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2 text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all duration-200"
        >
          {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span className="text-xs">Collapse</span></>}
        </button>
      </div>
    </motion.aside>
  );
}
