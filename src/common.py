from pathlib import Path
import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "warehouse.duckdb"
REPORTS = ROOT / "reports"
FIGS = REPORTS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

PALETTE = ["#1f4e79", "#e07b39", "#3a923a", "#b03a2e", "#7f7f7f", "#8e6bb8"]
plt.rcParams.update({
    "figure.figsize": (10, 5), "figure.dpi": 120, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
    "axes.prop_cycle": matplotlib.cycler(color=PALETTE), "font.size": 10,
})


def query(sql: str):
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql).df()


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / name, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved reports/figures/{name}")
