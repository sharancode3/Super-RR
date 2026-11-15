import pandas as pd
import json

df = pd.read_csv('scratch/rr_rebuild_recorded_20261115/delivery_impact_ledger.csv', low_memory=False)
ipl = df[df['comp_tier'] == 'IPL']

with open('dashboard/src/data/portraits_manifest.json') as f:
    manifest = json.load(f)

results = {}

for p in manifest:
    pid = p['player_id']
    pname = p['name']
    role = p['role']
    
    bat = ipl[ipl['striker_id'] == pid]
    bowl = ipl[ipl['bowler_id'] == pid]
    
    matches = len(set(bat['match_id'].unique().tolist() + bowl['match_id'].unique().tolist()))
    
    # Batting
    bat_innings = int(bat['match_id'].nunique())
    legal_bat = bat[bat['is_legal_ball'] == 1]
    runs = int(bat['offbat_runs'].sum())
    balls = int(len(legal_bat))
    fours = int(bat['is_four'].sum())
    sixes = int(bat['is_six'].sum())
    dismissals = int(bat['is_striker_dismissed'].sum())
    sr = round((runs / balls * 100), 2) if balls > 0 else 0.0
    avg = round((runs / dismissals), 2) if dismissals > 0 else (float(runs) if runs > 0 else 0.0)
    
    inn_runs = bat.groupby('match_id')['offbat_runs'].sum()
    hs = int(inn_runs.max()) if len(inn_runs) > 0 else 0
    fifties = int(((inn_runs >= 50) & (inn_runs < 100)).sum())
    hundreds = int((inn_runs >= 100).sum())
    
    hp_bat = bat[bat['is_high_pressure_20'] == 1]
    hp_bat_runs = int(hp_bat['offbat_runs'].sum())
    hp_bat_balls = int(len(hp_bat[hp_bat['is_legal_ball'] == 1]))
    hp_bat_sr = round((hp_bat_runs / hp_bat_balls * 100), 2) if hp_bat_balls > 0 else 0.0
    
    # Bowling
    bowl_innings = int(bowl['match_id'].nunique())
    legal_bowl = bowl[bowl['is_legal_ball'] == 1]
    balls_bowled = int(len(legal_bowl))
    overs = round(balls_bowled / 6.0, 1)
    runs_conceded = int(bowl['bowler_charge_runs'].sum())
    wickets = int(bowl['is_bowler_wicket'].sum())
    econ = round((runs_conceded / (balls_bowled / 6.0)), 2) if balls_bowled > 0 else 0.0
    bowl_avg = round((runs_conceded / wickets), 2) if wickets > 0 else 0.0
    bowl_sr = round((balls_bowled / wickets), 2) if wickets > 0 else 0.0
    
    inn_bowl = bowl.groupby('match_id').agg(w=('is_bowler_wicket', 'sum'), r=('bowler_charge_runs', 'sum'))
    if len(inn_bowl) > 0:
        sorted_inn = inn_bowl.sort_values(by=['w', 'r'], ascending=[False, True])
        top_w = int(sorted_inn.iloc[0]['w'])
        top_r = int(sorted_inn.iloc[0]['r'])
        bb = f"{top_w}/{top_r}"
        four_w = int((inn_bowl['w'] == 4).sum())
        five_w = int((inn_bowl['w'] >= 5).sum())
    else:
        bb = "—"
        four_w = 0
        five_w = 0
        
    hp_bowl = bowl[bowl['is_high_pressure_20'] == 1]
    hp_bowl_balls = int(len(hp_bowl[hp_bowl['is_legal_ball'] == 1]))
    hp_bowl_runs = int(hp_bowl['bowler_charge_runs'].sum())
    hp_bowl_w = int(hp_bowl['is_bowler_wicket'].sum())
    hp_bowl_econ = round((hp_bowl_runs / (hp_bowl_balls / 6.0)), 2) if hp_bowl_balls > 0 else 0.0
    
    is_primarily_batter = role == 'BATTER' or role == 'DUAL_ROLE'
    is_primarily_bowler = role == 'BOWLER' or role == 'DUAL_ROLE'
    
    results[str(pid)] = {
        'id': pid,
        'name': pname,
        'role': role,
        'matches': matches,
        'is_batter': is_primarily_batter,
        'is_bowler': is_primarily_bowler,
        'batting': {
            'innings': bat_innings,
            'runs': runs,
            'balls': balls,
            'fours': fours,
            'sixes': sixes,
            'strike_rate': sr,
            'average': avg,
            'highest_score': hs,
            'fifties': fifties,
            'hundreds': hundreds,
            'hp_balls': hp_bat_balls,
            'hp_runs': hp_bat_runs,
            'hp_strike_rate': hp_bat_sr
        },
        'bowling': {
            'innings': bowl_innings,
            'overs': overs,
            'balls': balls_bowled,
            'runs': runs_conceded,
            'wickets': wickets,
            'economy': econ,
            'average': bowl_avg,
            'strike_rate': bowl_sr,
            'best_bowling': bb,
            'four_w': four_w,
            'five_w': five_w,
            'hp_balls': hp_bowl_balls,
            'hp_wickets': hp_bowl_w,
            'hp_economy': hp_bowl_econ
        }
    }

output_path = 'dashboard/src/data/player_ipl_stats.json'
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Exported verified IPL stats for all {len(results)} manifest players to {output_path}")
