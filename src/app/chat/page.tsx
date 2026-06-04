"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface Message {
  role: "user" | "assistant";
  content: string;
  isBlocked?: boolean;
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if session exists
    const userJson = sessionStorage.getItem("user");
    if (!userJson) {
      router.push("/");
      return;
    }
    const parsedUser = JSON.parse(userJson);
    setUser(parsedUser);

    // Initial greeting
    setMessages([
      {
        role: "assistant",
        content:
          "Hello! I am your municipal assistant for **Pragati Nagar Nigam**. How can I help you with property taxes, water connections, trade licences, or birth certificates today?",
      },
    ]);
  }, [router]);

  useEffect(() => {
    // Auto-scroll to bottom on new message
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLogout = () => {
    sessionStorage.removeItem("user");
    router.push("/");
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || !user) return;

    setInput("");
    
    // Add user message locally
    const updatedMessages = [...messages, { role: "user", content: prompt } as Message];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: updatedMessages.map(m => ({ role: m.role, content: m.content })),
          user_id: user.id,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        if (data.decision === "ALLOWED") {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.response },
          ]);
        } else {
          // Blocked by G1, G2, or G3
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.response, isBlocked: true },
          ]);
        }
      } else {
        const errData = await response.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ System Error: ${errData.detail || "Server failed to process query"}`,
          },
        ]);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Error: Connection failed. Check if API backend is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Helper Markdown-to-HTML formatter
  const formatMarkdown = (text: string) => {
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Bold text (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // List elements (- text)
    html = html.replace(/^\s*-\s+(.*)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/g, "<ul class='list-disc ml-5 my-2'>$1</ul>");
    html = html.replace(/<\/ul>\s*<ul class='list-disc ml-5 my-2'>/g, "");

    // Headings (### text)
    html = html.replace(/^### (.*)$/gm, "<h3 class='text-amber-500 font-bold mt-3 mb-1 text-base'>$1</h3>");
    html = html.replace(/^## (.*)$/gm, "<h2 class='text-amber-500 font-bold mt-4 mb-2 text-lg'>$1</h2>");
    html = html.replace(/^# (.*)$/gm, "<h1 class='text-amber-500 font-bold mt-5 mb-3 text-xl'>$1</h1>");

    // Paragraph spacing
    html = html.replace(/\n\n/g, "<p class='mb-2'></p>");
    html = html.replace(/\n/g, "<br>");

    return <div dangerouslySetInnerHTML={{ __html: html }} />;
  };

  if (!user) return null;

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans">
      
      {/* Sidebar Navigation */}
      <aside className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col p-6">
        <div className="mb-8">
          <h2 className="text-xl font-bold tracking-tight text-amber-500 flex items-center gap-2">
            🏛️ PNN Portal
          </h2>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 mb-6">
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Welcome, Citizen</p>
          <div className="text-slate-100 text-sm font-semibold truncate mt-1">{user.email}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-2 truncate">ID: {user.id}</div>
        </div>

        <nav className="flex-1 space-y-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Supported Services</h3>
          <ul className="space-y-3 text-slate-400 text-sm">
            <li className="flex items-center gap-2">🏠 Property Tax Service</li>
            <li className="flex items-center gap-2">💧 Water Bill & Connection</li>
            <li className="flex items-center gap-2">🧹 Sanitation / Garbage</li>
            <li className="flex items-center gap-2">👶 Birth Certificate Service</li>
            <li className="flex items-center gap-2">💼 Trade Licence Service</li>
          </ul>
        </nav>

        <div className="space-y-3 mt-auto">
          <button
            onClick={() => router.push("/admin")}
            className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 active:scale-[0.99] transition-all py-2.5 font-semibold text-sm"
          >
            🔍 Admin Audit Logs
          </button>
          <button
            onClick={handleLogout}
            className="w-full rounded-lg bg-red-950/40 hover:bg-red-950/60 active:scale-[0.99] transition-all border border-red-500/20 py-2.5 font-semibold text-sm text-red-200"
          >
            Secure Logout
          </button>
        </div>
      </aside>

      {/* Main Chat Interface */}
      <main className="flex-1 flex flex-col h-full bg-slate-950">
        
        {/* Chat Header */}
        <header className="px-8 py-5 bg-slate-900 border-b border-slate-800">
          <h1 className="text-lg font-bold tracking-tight text-slate-100">
            🏛️ <span className="bg-gradient-to-r from-amber-500 to-amber-300 bg-clip-text text-transparent">Pragati Nagar Nigam</span> AI Assistant
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Ask about Property Taxes, Water Bills, Sanitation complaints, Birth Certificates, and Trade Licences.
          </p>
        </header>

        {/* Chat log */}
        <div className="flex-1 p-8 overflow-y-auto space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex flex-col max-w-[75%] animate-fade-in ${
                msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"
              }`}
            >
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-amber-500 text-slate-950 font-medium rounded-tr-sm"
                    : msg.isBlocked
                    ? "bg-orange-950/60 border border-orange-500/30 text-orange-200 rounded-tl-sm"
                    : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-sm"
                }`}
              >
                {formatMarkdown(msg.content)}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 px-4 py-3 rounded-2xl align-self-start mr-auto max-w-[75%] rounded-tl-sm">
              <span className="w-4 h-4 rounded-full border-2 border-amber-500 border-t-transparent animate-spin"></span>
              <span className="text-xs text-slate-400">Consulting official municipal guidelines...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Chat input box */}
        <footer className="px-8 py-5 bg-slate-900 border-t border-slate-800">
          <form onSubmit={handleSend} className="flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about property tax, water connection steps, trade license..."
              className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:border-amber-500 focus:outline-none"
              autoComplete="off"
            />
            <button
              type="submit"
              className="rounded-lg bg-amber-500 hover:bg-amber-600 active:scale-[0.99] px-6 text-sm font-semibold text-slate-950 transition-all"
            >
              Send Query
            </button>
          </form>
        </footer>
      </main>

    </div>
  );
}
