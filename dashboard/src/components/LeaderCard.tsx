import React from "react";
import type { RankingRecord, RoleType } from "../data/types";
import { PlayerCard } from "./PlayerCard";

interface LeaderCardProps {
  player: RankingRecord;
  role: RoleType;
  onPreview?: (player: RankingRecord) => void;
}

export const LeaderCard: React.FC<LeaderCardProps> = ({ player, role, onPreview }) => {
  return <PlayerCard player={player} role={role} isLeader={true} onPreview={onPreview} />;
};
