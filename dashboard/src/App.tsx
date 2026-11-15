import React, { useState } from "react";
import { Header } from "./components/Header";
import { FloatingSidebar } from "./components/FloatingSidebar";
import { HeroSection } from "./components/HeroSection";
import { RankedBoards } from "./components/RankedBoards";
import { ModelRankingsSection } from "./components/ModelRankingsSection";
import { MethodologySection } from "./components/MethodologySection";
import { MediaSection } from "./components/MediaSection";
import { PlayerPreviewModal } from "./components/PlayerPreviewModal";
import { Footer } from "./components/Footer";
import { evidence } from "./data";
import type { RankingRecord } from "./data/types";
import { useRevealObserver } from "./hooks/useRevealObserver";
import "./App.css";

export const App: React.FC = () => {
  useRevealObserver();
  const [previewPlayer, setPreviewPlayer] = useState<RankingRecord | null>(null);

  const batters = evidence.rankings
    .filter((r) => r.role === "batting")
    .sort((a, b) => a.rank - b.rank);

  const bowlers = evidence.rankings
    .filter((r) => r.role === "bowling")
    .sort((a, b) => a.rank - b.rank);

  return (
    <div className="app-layout">
      <FloatingSidebar />
      <Header />
      <main id="main-content" className="main-content">
        <HeroSection />
        <RankedBoards
          batters={batters}
          bowlers={bowlers}
          onPreviewPlayer={setPreviewPlayer}
        />
        <ModelRankingsSection />
        <MethodologySection evidence={evidence} />
        <MediaSection onPreviewPlayer={setPreviewPlayer} />
      </main>
      <Footer />
      {previewPlayer && (
        <PlayerPreviewModal
          player={previewPlayer}
          onClose={() => setPreviewPlayer(null)}
        />
      )}
    </div>
  );
};

export default App;
