import { ChatInterface } from "@/components/ChatInterface";
import { Sidebar } from "@/components/Sidebar";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col bg-ink-50 lg:flex-row dark:bg-ink-900">
      <Sidebar />
      <ChatInterface />
    </main>
  );
}
