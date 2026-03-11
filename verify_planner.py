import json
from brain import plan_goal
from parser import execute

def test_plan_generation():
    print("Testing Plan Generation...")
    goal = "find the cheapest PS5 on Amazon and add it to cart"
    plan = plan_goal(goal)
    print(f"Generated Plan for '{goal}':")
    print(json.dumps(plan, indent=2))
    assert len(plan) > 0
    assert any("amazon" in str(step).lower() for step in plan)
    print("Plan Generation Test Passed!\n")

if __name__ == "__main__":
    try:
        test_plan_generation()
    except Exception as e:
        print(f"Test failed: {e}")
