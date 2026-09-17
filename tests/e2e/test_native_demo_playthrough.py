import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from tests.e2e.support.native_demo_replay_child import drive


@pytest.mark.parametrize("profile,variation", [("difficulty.open-expedition",False),("difficulty.fragile-alliance",False),
    ("difficulty.silent-hunting-ground",False),("difficulty.open-expedition",True)])
async def test_native_cross_process_exact_public_and_complete_store(profile,variation):
    expected=await drive(profile,variation)
    root=Path(__file__).resolve().parents[2]
    for seed in ("1","937"):
        environment=os.environ.copy()
        for key in ("DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"):
            environment.pop(key,None)
        environment["PYTHONHASHSEED"]=seed
        environment["PYTHONIOENCODING"]="utf-8"
        command=[sys.executable,str(root/"tests/e2e/support/native_demo_replay_child.py"),profile]
        if variation: command.append("variation")
        child=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=90)
        assert child.returncode==0,child.stderr.decode("utf-8")
        assert json.loads(child.stdout)==expected
