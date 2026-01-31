"""Verification script for Solara backend logic."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from compute_permit_sim.vis.state import manager


async def test_backend():
    print("--- Starting Backend Verification ---")

    # 1. Initial State
    print(
        f"Initial State: Playing={manager.is_playing.value}, Step={manager.step_count.value}"
    )
    manager.reset_model()  # Explicit initialization
    assert manager.model.value is not None, "Model should be initialized"

    # 2. Load Scenario
    print("Testing Scenario Apply...")
    manager.apply_scenario("scenario_2")  # High Deterrence
    assert manager.selected_scenario.value == "scenario_2"
    assert manager.penalty.value == 0.8
    print("Scenario applied successfully.")

    # 3. Manual Step
    print("Testing Manual Step...")
    initial_step = manager.step_count.value
    manager.step()
    assert manager.step_count.value == initial_step + 1
    assert len(manager.compliance_history.value) == 1
    print(f"Step successful. New Step={manager.step_count.value}")

    # 4. Play Loop Simulation
    print("Testing Play Loop...")
    manager.is_playing.value = True

    # Run the loop for a short bit
    task = asyncio.create_task(manager.play_loop())
    await asyncio.sleep(0.5)  # Let it run for a few steps

    manager.is_playing.value = False
    await task

    print(f"Steps after play: {manager.step_count.value}")
    assert manager.step_count.value > initial_step + 1, (
        "Should have advanced multiple steps"
    )

    # 5. Reset
    print("Testing Reset...")
    manager.reset_model()
    assert manager.step_count.value == 0
    assert len(manager.compliance_history.value) == 0
    print("Reset successful.")

    print("--- Verification Passed ---")


if __name__ == "__main__":
    asyncio.run(test_backend())
