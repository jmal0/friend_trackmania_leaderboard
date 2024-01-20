import argparse
import collections
import dataclasses
import datetime
import heapq
import itertools
import pathlib
from typing import Any

import numpy as np
import plotly.graph_objects as go
import plotly.io
import requests
import toml
import yaml


def main() -> None:
    args = parse_args()
    with open(args.config) as cfg_file:
        cfg = Config.from_toml(toml.load(cfg_file))

    cache_file = pathlib.Path("cached.yml")
    if not cache_file.exists():
        trophy_results: dict[str, list[TrophyData]] = {}
        for name, player_id in cfg.player_ids.items():
            print(f"Fetching trophy results for {name}")
            trophy_results[name] = get_trophies(player_id)

        with open("cached.yml", "w") as out:
            yamlified = {
                player: [dataclasses.asdict(trophy) for trophy in player_trophies]
                for player, player_trophies in trophy_results.items()
            }
            yaml.dump(yamlified, out)
    else:
        with open(cache_file) as yaml_in:
            parsed_yaml = yaml.safe_load(yaml_in)
        trophy_results = {
            player: [TrophyData(**trophy) for trophy in player_data]
            for player, player_data in parsed_yaml.items()
        }

    print("Plotting")
    figs = plot_trophies(trophy_results, cfg.plot_settings)
    for plot_name, fig in figs.items():
        with open(f"{plot_name}.html", "wb") as out_html:
            out_html.write(plotly.io.to_html(fig).encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    _cfg_dir = pathlib.Path(__file__).parent / "cfg"
    parser.add_argument(
        "--config",
        "-c",
        default=_cfg_dir / "cfg.toml",
        type=pathlib.Path,
        help="toml configuration file",
    )
    return parser.parse_args()


@dataclasses.dataclass
class Config:
    player_ids: dict[str, str]
    plot_settings: dict[str, Any]

    @classmethod
    def from_toml(cls, cfg: dict):
        return cls(
            player_ids={str(name): player_id for name, player_id in cfg["players"]},
            plot_settings=cfg.get("plot_settings", {}),
        )


@dataclasses.dataclass
class TrophyData:
    timestamp: datetime.datetime
    achievement_type: str
    count: int
    data: dict

    @classmethod
    def from_gain(cls, gain_data: dict):
        return cls(
            timestamp=datetime.datetime.fromisoformat(gain_data["timestamp"]),
            achievement_type=gain_data["achievement"]["trophyAchievementType"],
            count=_sum_trophy_points(gain_data["counts"]),
            data=gain_data,
        )

    def __lt__(self, other: "TrophyData") -> bool:
        return self.timestamp < other.timestamp

    @staticmethod
    def categorize(gain_data: dict[str, Any]) -> str:
        achieve = gain_data["achievement"]
        category = achieve["trophyAchievementType"]
        match category:
            case "SoloRanking":
                return f"SoloRanking - {achieve['trophySoloRankingAchievementType']}"
            case _:
                return category


def _sum_trophy_points(counts: list[int]) -> int:
    expected_len = 9
    if len(counts) != expected_len:
        raise ValueError()
    return sum(counts[i] * 10**i for i in range(expected_len))


def get_trophies(player_id, request_limit: int = 100) -> list[TrophyData]:
    base_url = f"https://trackmania.io/api/player/{player_id}/trophies"
    headers = {
        "User-Agent": "friend_trackmania_leaderboard/jmal0320@gmail.com",
    }

    gains = []
    for page in range(0, request_limit):
        resp = requests.get(url=f"{base_url}/{page}", headers=headers, data={})
        if not resp.ok:
            raise RuntimeError(f"Trophies request failed. Response: {resp.json()}")
        data = resp.json()
        num_gains = data["total"]
        for entry in data["gains"]:
            gains.append(TrophyData.from_gain(entry))
        if len(gains) == num_gains:
            break
    return gains


def plot_trophies(
    player_trophies: dict[str, list[TrophyData]], plot_args: dict[str, Any]
) -> dict[str, go.Figure]:
    categories = set()
    for player_results in player_trophies.values():
        categories = categories.union(res.achievement_type for res in player_results)

    trophies_chronological = {
        player: sorted(trophies, key=lambda res: res.timestamp)
        for player, trophies in player_trophies.items()
    }
    return {
        "cumulative": plot_cumulative_trophies(trophies_chronological),
        "john_v_marc": plot_race(trophies_chronological, "jmal", "sampleses"),
        "categorized": plot_categorized_trophies(
            list(categories),
            trophies_chronological,
            datetime.datetime.fromisoformat(plot_args["categorized"]["start_date"]),
        ),
    }


def plot_race(
    player_trophies_chronological: dict[str, list[TrophyData]],
    player1: str,
    player2: str,
) -> go.Figure:
    player1_results = zip(itertools.repeat(0), player_trophies_chronological[player1])
    player2_results = zip(itertools.repeat(1), player_trophies_chronological[player2])
    sums = [0, 0]
    t = []
    deltas = []
    for player, trophy in heapq.merge(
        player1_results, player2_results, key=lambda v: v[1].timestamp
    ):
        sums[player] += trophy.count
        t.append(trophy.timestamp)
        deltas.append(sums[0] - sums[1])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=t,
            y=deltas,
        )
    )
    fig.update_yaxes(title_text=f"{player1} trophies minus {player2} trophies")
    return fig


def plot_cumulative_trophies(player_trophies: dict[str, list[TrophyData]]) -> go.Figure:
    fig = go.Figure()
    for player, trophies in player_trophies.items():
        trophies_chronological = sorted(trophies, key=lambda res: res.timestamp)
        fig.add_trace(
            go.Scatter(
                x=[trophy.timestamp for trophy in trophies_chronological],
                y=np.cumsum([trophy.count for trophy in trophies_chronological]),
                name=player,
            )
        )
        fig.update_yaxes(title_text="Trophy points")
    return fig


def plot_categorized_trophies(
    categories: list[str],
    player_trophies: dict[str, list[TrophyData]],
    start_date: datetime.datetime,
) -> go.Figure:
    fig = go.Figure()
    for player, trophies in player_trophies.items():
        trophies_after_start = [
            trophy for trophy in trophies if trophy.timestamp >= start_date
        ]
        totals = collections.defaultdict(int)
        for trophy in trophies_after_start:
            totals[trophy.achievement_type] += trophy.count
        fig.add_trace(
            go.Bar(name=player, x=categories, y=[totals[cat] for cat in categories]),
        )
        fig.update_yaxes(title_text="Trophy points")
    return fig


if __name__ == "__main__":
    main()
