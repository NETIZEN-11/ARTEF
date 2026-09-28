"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Terminal,
  Activity,
  ArrowRight,
  Play,
  CheckCircle2,
  Layers,
  Cpu,
  GitBranch,
  Users,
  ChevronDown,
  Sparkles,
  ExternalLink,
  Code2,
  Flame,
  BarChart3,
  Database,
} from "lucide-react";
import {
  ATTACK_SCENARIOS,
  FAQS,
  HERO_STATS,
  FRAMEWORK_BADGES,
  NAV_LINKS,
  WORKFLOW_STEPS,
  BENCHMARK_COMPARISONS,
} from "@/data/landing-content";

export default function LandingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [selectedScenario, setSelectedScenario] = useState(ATTACK_SCENARIOS[0]);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const handleLaunch = () => {
    router.push(isAuthenticated ? "/dashboard" : "/login");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-pink-50 to-white text-gray-900 font-sans antialiased selection:bg-pink-400 selection:text-white">
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-gradient-to-br from-pink-300/40 via-rose-200/30 to-transparent blur-[120px] rounded-full" />
        <div className="absolute top-1/2 -left-60 w-[500px] h-[400px] bg-pink-200/30 blur-[100px] rounded-full" />
        <div className="absolute bottom-0 -right-40 w-[600px] h-[500px] bg-rose-200/20 blur-[120px] rounded-full" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#f9a8d420_1px,transparent_1px),linear-gradient(to_bottom,#f9a8d420_1px,transparent_1px)] bg-[size:3rem_3rem]" />
      </div>

      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/70 border-b border-pink-100 shadow-sm shadow-pink-100/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 via-pink-500 to-pink-400 p-[1.5px] shadow-lg shadow-pink-300/40 group-hover:scale-105 transition-transform">
              <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center">
                <Shield className="w-5 h-5 text-pink-600" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-rose-600 to-pink-500 bg-clip-text text-transparent">
                  ARTEF
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-pink-50 text-pink-600 border border-pink-200">
                  OJT 2026
                </span>
              </div>
              <p className="text-[11px] text-gray-400 hidden sm:block leading-none">Agent Red-Teaming &amp; Assurance</p>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-7 text-sm font-medium text-gray-500">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="hover:text-rose-600 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <button
            onClick={handleLaunch}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-400 hover:to-pink-400 text-white shadow-lg shadow-pink-300/40 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <span>{isAuthenticated ? "Dashboard" : "Enter Console"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="relative z-10">
        <section className="pt-16 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7 space-y-7">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-pink-100 to-rose-100 border border-pink-200 text-pink-700 text-xs font-semibold shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-rose-500" />
                <span>Autonomous Agent Red-Teaming Platform</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1] text-gray-900">
                Secure AI Agents{" "}
                <span className="bg-gradient-to-r from-rose-500 via-pink-500 to-fuchsia-500 bg-clip-text text-transparent">
                  Before Adversaries Exploit Them.
                </span>
              </h1>

              <p className="text-base sm:text-lg text-gray-500 leading-relaxed max-w-2xl">
                ARTEF autonomously probes, jailbreaks, and stress-tests your LLM agents across multi-turn trajectories, tool execution, and RAG pipelines with CI/CD safety gates to block risky deployments automatically.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 pt-1">
                <button
                  onClick={handleLaunch}
                  className="px-8 py-3.5 rounded-xl font-semibold text-base bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-400 hover:to-pink-400 text-white shadow-xl shadow-pink-300/50 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center space-x-2 group"
                >
                  <Play className="w-4 h-4 fill-white" />
                  <span>Launch ARTEF Console</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
                <a
                  href="#simulator"
                  className="px-6 py-3.5 rounded-xl font-medium text-base bg-white hover:bg-pink-50 border border-pink-200 hover:border-pink-300 text-gray-700 hover:text-rose-600 shadow-sm transition-all flex items-center justify-center space-x-2"
                >
                  <Terminal className="w-4 h-4 text-pink-500" />
                  <span>Try Live Simulator</span>
                </a>
              </div>

              <div className="pt-4 border-t border-pink-100 grid grid-cols-2 sm:grid-cols-4 gap-4">
                {HERO_STATS.map((s) => (
                  <div key={s.label} className="p-4 rounded-2xl bg-white border border-pink-100 shadow-sm hover:shadow-md hover:border-pink-200 transition-all">
                    <div className={`text-2xl font-extrabold ${s.color}`}>{s.val}</div>
                    <div className="text-xs text-gray-400 font-medium mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-5 relative flex justify-center">
              <div className="absolute -inset-6 bg-gradient-to-r from-pink-400/30 via-rose-400/20 to-fuchsia-300/20 rounded-3xl blur-3xl opacity-60 animate-pulse" />

              <div className="relative w-full max-w-md rounded-3xl bg-white border border-pink-200 shadow-2xl shadow-pink-200/60 p-5 hover:border-rose-300 transition-all group">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-pink-100 text-xs font-semibold">
                  <span className="flex items-center space-x-1.5 text-rose-600 bg-rose-50 px-3 py-1 rounded-full border border-rose-200">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                    <span>Red-Team Vectors</span>
                  </span>
                  <span className="flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Eval Active</span>
                  </span>
                </div>

                <div className="rounded-2xl overflow-hidden border border-pink-100 bg-gray-50 flex items-center justify-center p-2">
                  <img
                    src="/images/artef-diagram.png"
                    alt="ARTEF Architecture Diagram"
                    className="w-full h-auto object-contain transition-transform duration-500 group-hover:scale-[1.03]"
                  />
                </div>

                <div className="mt-3 px-4 py-2.5 rounded-xl bg-gradient-to-r from-pink-50 to-rose-50 border border-pink-100 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-semibold text-gray-700">ARTEF Engine:</span>
                    <span className="text-emerald-700 font-bold">PROTECTION ACTIVE</span>
                  </div>
                  <span className="text-gray-400 font-mono text-[11px]">v1.0-OJT</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="pb-12 px-4 max-w-7xl mx-auto">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-gray-400 mb-6">
            Built on battle-tested frameworks
          </p>
          <div className="flex flex-wrap items-center justify-center gap-5">
            {FRAMEWORK_BADGES.map((tech) => (
              <span
                key={tech}
                className="px-4 py-2 rounded-xl bg-white border border-pink-100 shadow-sm text-sm font-semibold text-gray-500 hover:text-rose-600 hover:border-pink-300 transition-all"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>

        <section id="simulator" className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-pink-600 bg-pink-50 px-4 py-1.5 rounded-full border border-pink-200 mb-4">
              <Terminal className="w-3.5 h-3.5" />
              <span>Interactive Threat Simulation</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900">
              Watch ARTEF Intercept Real Exploits
            </h2>
            <p className="mt-3 text-gray-500 text-base">
              Select an attack scenario to see real-time threat interception, scoring, and neutralization.
            </p>
          </div>

          <div className="rounded-3xl border border-pink-200 bg-white shadow-2xl shadow-pink-100/60 overflow-hidden">
            <div className="flex border-b border-pink-100 bg-pink-50/60 overflow-x-auto scrollbar-hide">
              {ATTACK_SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedScenario(s)}
                  className={`px-5 py-3.5 text-xs sm:text-sm font-semibold whitespace-nowrap transition-colors flex items-center space-x-2 border-b-2 ${
                    selectedScenario.id === s.id
                      ? "border-rose-500 text-rose-700 bg-white"
                      : "border-transparent text-gray-400 hover:text-rose-500 hover:bg-white/50"
                  }`}
                >
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>{s.title}</span>
                </button>
              ))}
            </div>

            <div className="px-6 py-2.5 bg-gray-900 flex items-center justify-between text-xs text-gray-400 font-mono">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-red-400 inline-block" />
                <span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" />
                <span className="w-3 h-3 rounded-full bg-green-400 inline-block" />
                <span className="ml-3 text-gray-400 font-sans font-medium">ARTEF Probe Console - {selectedScenario.vector}</span>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-emerald-400 flex items-center space-x-1">
                  <Activity className="w-3.5 h-3.5 animate-pulse" />
                  <span>{selectedScenario.latency}</span>
                </span>
                <span className="px-2.5 py-0.5 rounded bg-pink-900/40 text-pink-300 border border-pink-700/40 font-semibold">
                  {selectedScenario.badge}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-pink-100">
              <div className="p-6 sm:p-8 space-y-4 bg-white">
                <div className="flex items-center space-x-2 text-rose-600 text-xs font-bold uppercase tracking-wider">
                  <Flame className="w-4 h-4" />
                  <span>Injected Adversarial Payload</span>
                </div>
                <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 font-mono text-sm text-rose-700 leading-relaxed shadow-inner">
                  <p className="text-xs text-rose-400 mb-2 font-bold">Input Payload</p>
                  &quot;{selectedScenario.attackPrompt}&quot;
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Threat Classifier: <span className="font-bold text-amber-600">{selectedScenario.score} Score</span></span>
                  <span className="font-mono">{selectedScenario.vector}</span>
                </div>
              </div>

              <div className="p-6 sm:p-8 space-y-4 bg-emerald-50/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-emerald-700 text-xs font-bold uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4" />
                    <span>ARTEF Guardrail Verdict</span>
                  </div>
                  <span className="px-3 py-0.5 rounded-full text-xs font-bold uppercase bg-emerald-100 text-emerald-700 border border-emerald-300">
                    {selectedScenario.status}
                  </span>
                </div>
                <div className="rounded-xl bg-white border border-emerald-200 p-4 font-mono text-sm text-emerald-800 leading-relaxed shadow-inner">
                  <p className="text-xs text-emerald-500 mb-2 font-bold">Guardrail Trace</p>
                  &quot;{selectedScenario.defenseResponse}&quot;
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-white border border-pink-100 shadow-sm">
                    <div className="text-[11px] text-gray-400 uppercase font-semibold">Confidence</div>
                    <div className="text-lg font-bold text-gray-900 mt-0.5">99.8%</div>
                  </div>
                  <div className="p-3 rounded-xl bg-white border border-pink-100 shadow-sm">
                    <div className="text-[11px] text-gray-400 uppercase font-semibold">Action</div>
                    <div className="text-lg font-bold text-emerald-600 mt-0.5">Drop &amp; Log</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-rose-600 bg-rose-50 px-4 py-1.5 rounded-full border border-rose-200 mb-4">
              <Layers className="w-3.5 h-3.5" />
              <span>Full-Stack AI Assurance</span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-gray-900">
              Engineered for Enterprise LLM Resilience
            </h2>
            <p className="mt-4 text-gray-500 text-base sm:text-lg">
              Every component needed to evaluate, defend, and audit autonomous agent workflows from dev to production.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 rounded-3xl p-8 bg-white border border-pink-100 shadow-lg hover:shadow-xl hover:border-rose-300 transition-all group">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 mb-6 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">Autonomous Multi-Turn Red-Teaming</h3>
              <p className="text-gray-500 leading-relaxed">
                Simulates real attacker personas that converse dynamically with your agent. Fuzzes tool calls, uses token smuggling, and attempts recursive state bypasses over dozens of turns.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {["Token Smuggling", "Crescendo Attacks", "Autonomous Fuzzing"].map((t) => (
                  <span key={t} className="text-xs px-3 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-medium">{t}</span>
                ))}
              </div>
            </div>

            <div className="rounded-3xl p-8 bg-gradient-to-br from-pink-500 to-rose-600 border-0 shadow-lg text-white group hover:scale-[1.01] transition-all">
              <div className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Cpu className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-3">Multi-Judge Consensus</h3>
              <p className="text-pink-100 text-sm leading-relaxed">
                Eliminates single-model judge hallucination by combining ensemble LLM evaluators with deterministic regex, refusal classifiers, and vector semantic similarity.
              </p>
            </div>

            <div className="rounded-3xl p-8 bg-white border border-pink-100 shadow-lg hover:shadow-xl hover:border-pink-300 transition-all group">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-6 group-hover:scale-110 transition-transform">
                <GitBranch className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">CI/CD Safety Gate</h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                Embed ARTEF in GitHub Actions or GitLab CI. Enforce 0% tolerance for critical safety regressions before model or prompt updates go live.
              </p>
            </div>

            <div className="md:col-span-2 rounded-3xl p-8 bg-white border border-pink-100 shadow-lg hover:shadow-xl hover:border-pink-300 transition-all group">
              <div className="w-12 h-12 rounded-2xl bg-pink-50 border border-pink-200 flex items-center justify-center text-pink-600 mb-6 group-hover:scale-110 transition-transform">
                <Users className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">Human Review &amp; Triage Queue</h3>
              <p className="text-gray-500 leading-relaxed">
                Borderline results are auto-routed to a human review queue. Security teams inspect full agent trajectories and calibrate judge weights with one click.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {["Trajectory Inspector", "RBAC Permissions", "Audit Logging"].map((t) => (
                  <span key={t} className="text-xs px-3 py-1 rounded-lg bg-pink-50 border border-pink-200 text-pink-700 font-medium">{t}</span>
                ))}
              </div>
            </div>

            <div className="rounded-3xl p-8 bg-white border border-pink-100 shadow-lg hover:shadow-xl hover:border-pink-300 transition-all group">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mb-6 group-hover:scale-110 transition-transform">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Analytics Dashboard</h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                Real-time risk heatmaps, attack success rate trends, severity breakdowns, and downloadable audit compliance reports.
              </p>
            </div>

            <div className="rounded-3xl p-8 bg-white border border-pink-100 shadow-lg hover:shadow-xl hover:border-pink-300 transition-all group">
              <div className="w-12 h-12 rounded-2xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 mb-6 group-hover:scale-110 transition-transform">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">RAG Security Testing</h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                Test ChromaDB retrieval pipelines for document poisoning, chunk manipulation, and semantic-drift attacks in vector-augmented agents.
              </p>
            </div>
          </div>
        </section>

        <section id="architecture" className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-4 py-1.5 rounded-full border border-emerald-200 mb-4">
              <Activity className="w-3.5 h-3.5" />
              <span>How It Works</span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-gray-900">Secure Your Agent in 4 Steps</h2>
            <p className="mt-4 text-gray-500 text-base">From endpoint connection to continuous deployment protection.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {WORKFLOW_STEPS.map((step) => (
              <div
                key={step.num}
                className="p-7 rounded-3xl bg-white border border-pink-100 shadow-sm hover:shadow-lg hover:border-pink-200 transition-all relative overflow-hidden group"
              >
                <div className={`absolute top-4 right-4 text-5xl font-black opacity-5 group-hover:opacity-10 transition-opacity text-${step.color}-500`}>
                  {step.num}
                </div>
                <div className={`text-3xl font-black bg-gradient-to-r from-${step.color}-500 to-pink-500 bg-clip-text text-transparent mb-4`}>
                  {step.num}
                </div>
                <h4 className="text-lg font-bold text-gray-900 mb-2">{step.title}</h4>
                <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="benchmarks" className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900">
              Why Traditional Testing Falls Short
            </h2>
            <p className="mt-3 text-gray-500">Comparing evaluation tools against ARTEF&apos;s autonomous red-teaming engine.</p>
          </div>

          <div className="rounded-3xl border border-pink-100 bg-white shadow-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-gradient-to-r from-pink-50 to-rose-50 text-xs uppercase font-bold text-gray-500 border-b border-pink-100">
                <tr>
                  <th className="py-4 px-6">Evaluation Feature</th>
                  <th className="py-4 px-6 text-rose-600">ARTEF Platform</th>
                  <th className="py-4 px-6 text-gray-400">Static Scanners</th>
                  <th className="py-4 px-6 text-gray-400">Manual Pentesting</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pink-50">
                {BENCHMARK_COMPARISONS.map((row) => (
                  <tr key={row.feat} className="hover:bg-pink-50/40 transition-colors">
                    <td className="py-4 px-6 font-semibold text-gray-800">{row.feat}</td>
                    <td className="py-4 px-6 text-emerald-700 font-semibold">{row.artef}</td>
                    <td className="py-4 px-6 text-gray-400">{row.s}</td>
                    <td className="py-4 px-6 text-gray-400">{row.m}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="rounded-3xl p-8 sm:p-12 bg-gradient-to-r from-rose-500 via-pink-500 to-fuchsia-500 shadow-2xl shadow-pink-300/40 flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="space-y-3 max-w-2xl">
              <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-pink-100 bg-white/10 px-3 py-1.5 rounded-full border border-white/20">
                <Code2 className="w-3.5 h-3.5" />
                <span>On-the-Job Training Deliverable - 2026</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-white">
                Designed &amp; Built by Nitesh Singh
              </h3>
              <p className="text-pink-100 text-sm sm:text-base leading-relaxed">
                ARTEF was conceived and implemented as a production-grade AI security system combining FastAPI, Next.js 14, Celery workers, ChromaDB vector indexing, RBAC authentication, and real-time adversarial evaluation matrices.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleLaunch}
                className="px-6 py-3 rounded-xl font-semibold text-sm bg-white text-rose-600 hover:bg-pink-50 shadow-lg transition-all flex items-center space-x-2"
              >
                <span>Launch Console</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <a
                href="https://github.com/NETIZEN-11/ARTEF"
                target="_blank"
                rel="noreferrer"
                className="px-6 py-3 rounded-xl font-medium text-sm bg-white/10 hover:bg-white/20 border border-white/30 text-white transition-all flex items-center space-x-2"
              >
                <ExternalLink className="w-4 h-4" />
                <span>GitHub Repository</span>
              </a>
            </div>
          </div>
        </section>

        <section id="faq" className="py-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-extrabold text-gray-900">Frequently Asked Questions</h2>
            <p className="mt-2 text-gray-500 text-sm">Everything you need to know about the platform.</p>
          </div>
          <div className="space-y-3">
            {FAQS.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-2xl border border-pink-100 bg-white shadow-sm overflow-hidden hover:border-pink-200 transition-colors"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full py-4 px-6 text-left flex items-center justify-between text-base font-semibold text-gray-800 hover:text-rose-600 transition-colors"
                >
                  <span>{faq.question}</span>
                  <ChevronDown className={`w-5 h-5 text-pink-400 transition-transform duration-200 ${openFaq === idx ? "rotate-180 text-rose-500" : ""}`} />
                </button>
                {openFaq === idx && (
                  <div className="px-6 pb-5 text-sm text-gray-500 leading-relaxed border-t border-pink-100 pt-3">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto text-center">
          <div className="rounded-3xl p-10 sm:p-16 bg-gradient-to-b from-pink-50 to-rose-50 border border-pink-200 shadow-xl relative overflow-hidden">
            <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-96 h-64 bg-pink-300/30 blur-3xl rounded-full pointer-events-none" />
            <div className="relative">
              <h2 className="text-3xl sm:text-5xl font-extrabold text-gray-900 tracking-tight">
                Ready to{" "}
                <span className="bg-gradient-to-r from-rose-500 to-pink-600 bg-clip-text text-transparent">
                  Stress-Test
                </span>{" "}
                Your AI Agents?
              </h2>
              <p className="mt-4 text-gray-500 text-base sm:text-lg max-w-2xl mx-auto">
                Start automated red-teaming today and protect your autonomous systems against multi-turn jailbreaks, prompt injections, and data leaks.
              </p>
              <button
                onClick={handleLaunch}
                className="mt-8 px-10 py-4 rounded-2xl font-bold text-base bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-400 hover:to-pink-400 text-white shadow-2xl shadow-pink-300/50 hover:scale-105 active:scale-95 transition-all flex items-center space-x-2 mx-auto"
              >
                <span>Launch ARTEF Platform</span>
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-pink-100 bg-white py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-gray-900 text-sm">ARTEF</span>
              <p className="text-xs text-gray-400">Continuous AI Agent Assurance &amp; Threat Defense</p>
            </div>
          </div>

          <p className="text-xs text-gray-400">
            Copyright &copy; 2026 <strong className="text-gray-700">Nitesh Singh</strong>. All Rights Reserved. (OJT Deliverable)
          </p>

          <div className="flex items-center space-x-6 text-xs text-gray-400">
            <a href="https://github.com/NETIZEN-11/ARTEF" target="_blank" rel="noreferrer" className="hover:text-rose-600 transition-colors font-medium">GitHub</a>
            <Link href="/dashboard" className="hover:text-rose-600 transition-colors font-medium">Dashboard</Link>
            <Link href="/login" className="hover:text-rose-600 transition-colors font-medium">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}