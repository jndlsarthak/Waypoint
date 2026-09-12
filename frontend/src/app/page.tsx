import { ChatPanel } from "@/components/chat/ChatPanel";
import { DisclaimerBar } from "@/components/DisclaimerBar";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { StatsStrip } from "@/components/StatsStrip";

export default function Home() {
  return (
    <>
      <Header />
      <DisclaimerBar />
      <main className="flex-1">
        <Hero />
        <StatsStrip />
        <ChatPanel />
      </main>
      <Footer />
    </>
  );
}
