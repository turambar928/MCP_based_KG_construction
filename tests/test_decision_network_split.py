import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).parents[1] / "exps" / "decision_network" / "train_fphi.py"
SPEC = importlib.util.spec_from_file_location("train_fphi", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_group_split_keeps_clean_and_dirty_variants_together():
    rows = []
    for domain in ("government", "finance", "environment"):
        for i in range(20):
            for label in (0, 1):
                rows.append({"uid": f"{domain}-{i}", "domain": domain, "y_repair": label})
    df = pd.DataFrame(rows)
    train, val, test = MODULE.stratified_group_split(df)
    uid_sets = [set(df.iloc[index]["uid"]) for index in (train, val, test)]

    assert not (uid_sets[0] & uid_sets[1])
    assert not (uid_sets[0] & uid_sets[2])
    assert not (uid_sets[1] & uid_sets[2])
    assert sum(map(len, (train, val, test))) == len(df)
