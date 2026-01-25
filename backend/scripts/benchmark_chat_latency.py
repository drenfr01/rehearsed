#!/usr/bin/env python3
"""Benchmark script to measure chat endpoint latency.

This script measures cold-start vs warm performance of the chat endpoint
to help identify latency bottlenecks.

Usage:
    # Run from the backend directory:
    python scripts/benchmark_chat_latency.py
    
    # Or with specific options:
    python scripts/benchmark_chat_latency.py --warm-iterations 5 --scenario-id 1
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the app directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment before importing app modules
os.environ.setdefault("APP_ENV", "development")


def run_cold_start_test(scenario_id: int = 1) -> dict:
    """Run a cold start test by spawning a fresh Python process.
    
    Args:
        scenario_id: The scenario ID to use for the test.
        
    Returns:
        dict: Timing results from the cold start test.
    """
    print("\n" + "=" * 60)
    print("COLD START TEST")
    print("=" * 60)
    print("Spawning fresh Python process...")
    
    # Create a small script to run the test
    test_script = f'''
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("APP_ENV", "development")

async def test():
    from app.core.langgraph.graph_entry import LangGraphAgent
    from app.services.gemini_text_to_speech import GeminiTextToSpeech
    from app.schemas import Message
    
    total_start = time.perf_counter()
    
    agent = LangGraphAgent()
    tts_service = GeminiTextToSpeech()
    
    messages = [
        Message(role="user", content="Hello, can you tell me about photosynthesis?")
    ]
    
    try:
        response = await agent.get_response(
            messages=messages,
            session_id="benchmark-cold-" + str(int(time.time())),
            user_id="benchmark-user",
            scenario_id={scenario_id},
            tts_service=tts_service,
        )
        total_duration = time.perf_counter() - total_start
        print(f"COLD_START_TOTAL_MS={{total_duration * 1000:.2f}}")
        print(f"SUCCESS=true")
    except Exception as e:
        total_duration = time.perf_counter() - total_start
        print(f"COLD_START_TOTAL_MS={{total_duration * 1000:.2f}}")
        print(f"SUCCESS=false")
        print(f"ERROR={{str(e)}}")

asyncio.run(test())
'''
    
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    process_duration = time.perf_counter() - start
    
    # Parse output
    output = result.stdout + result.stderr
    print(f"Process output:\n{output}")
    
    cold_start_ms = None
    success = False
    for line in output.split("\n"):
        if line.startswith("COLD_START_TOTAL_MS="):
            cold_start_ms = float(line.split("=")[1])
        if line.startswith("SUCCESS=true"):
            success = True
    
    return {
        "cold_start_ms": cold_start_ms,
        "process_total_ms": process_duration * 1000,
        "success": success,
    }


async def run_warm_test(iterations: int = 3, scenario_id: int = 1) -> dict:
    """Run warm tests by reusing the same agent instance.
    
    Args:
        iterations: Number of warm iterations to run.
        scenario_id: The scenario ID to use for the test.
        
    Returns:
        dict: Timing results from the warm tests.
    """
    print("\n" + "=" * 60)
    print(f"WARM TEST ({iterations} iterations)")
    print("=" * 60)
    
    from app.core.langgraph.graph_entry import LangGraphAgent
    from app.services.gemini_text_to_speech import GeminiTextToSpeech
    from app.schemas import Message
    
    # First request (includes initialization)
    print("\nFirst request (includes lazy initialization)...")
    agent = LangGraphAgent()
    tts_service = GeminiTextToSpeech()
    
    messages = [
        Message(role="user", content="Hello, can you tell me about photosynthesis?")
    ]
    
    first_start = time.perf_counter()
    try:
        await agent.get_response(
            messages=messages,
            session_id=f"benchmark-warm-first-{int(time.time())}",
            user_id="benchmark-user",
            scenario_id=scenario_id,
            tts_service=tts_service,
        )
        first_duration = time.perf_counter() - first_start
        first_success = True
        print(f"First request: {first_duration * 1000:.2f}ms")
    except Exception as e:
        first_duration = time.perf_counter() - first_start
        first_success = False
        print(f"First request failed: {e}")
    
    # Subsequent requests (warm)
    warm_times = []
    for i in range(iterations):
        print(f"\nWarm request {i + 1}/{iterations}...")
        
        # Use different session IDs to avoid checkpoint issues
        start = time.perf_counter()
        try:
            await agent.get_response(
                messages=messages,
                session_id=f"benchmark-warm-{i}-{int(time.time())}",
                user_id="benchmark-user",
                scenario_id=scenario_id,
                tts_service=tts_service,
            )
            duration = time.perf_counter() - start
            warm_times.append(duration * 1000)
            print(f"Request {i + 1}: {duration * 1000:.2f}ms")
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"Request {i + 1} failed after {duration * 1000:.2f}ms: {e}")
    
    return {
        "first_request_ms": first_duration * 1000,
        "first_success": first_success,
        "warm_times_ms": warm_times,
        "warm_avg_ms": sum(warm_times) / len(warm_times) if warm_times else None,
        "warm_min_ms": min(warm_times) if warm_times else None,
        "warm_max_ms": max(warm_times) if warm_times else None,
    }


def print_report(cold_results: dict, warm_results: dict):
    """Print a summary report of the benchmark results.
    
    Args:
        cold_results: Results from cold start test.
        warm_results: Results from warm tests.
    """
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    
    print("\nCOLD START:")
    if cold_results.get("cold_start_ms"):
        print(f"  Total time: {cold_results['cold_start_ms']:.2f}ms")
        print(f"  Process overhead: {cold_results['process_total_ms'] - cold_results['cold_start_ms']:.2f}ms")
    else:
        print("  Failed to get cold start timing")
    
    print("\nWARM (after initialization):")
    print(f"  First request: {warm_results['first_request_ms']:.2f}ms")
    if warm_results.get("warm_times_ms"):
        print(f"  Subsequent avg: {warm_results['warm_avg_ms']:.2f}ms")
        print(f"  Subsequent min: {warm_results['warm_min_ms']:.2f}ms")
        print(f"  Subsequent max: {warm_results['warm_max_ms']:.2f}ms")
    
    if cold_results.get("cold_start_ms") and warm_results.get("warm_avg_ms"):
        overhead = cold_results["cold_start_ms"] - warm_results["warm_avg_ms"]
        print(f"\nCOLD START OVERHEAD: {overhead:.2f}ms")
        print(f"  (cold start is {cold_results['cold_start_ms'] / warm_results['warm_avg_ms']:.1f}x slower than warm)")
    
    print("\n" + "=" * 60)
    print("Check the logs above for detailed timing breakdowns")
    print("Look for 'timing_measurement' log entries")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Benchmark chat endpoint latency")
    parser.add_argument(
        "--warm-iterations",
        type=int,
        default=3,
        help="Number of warm iterations to run (default: 3)",
    )
    parser.add_argument(
        "--scenario-id",
        type=int,
        default=1,
        help="Scenario ID to use for tests (default: 1)",
    )
    parser.add_argument(
        "--skip-cold",
        action="store_true",
        help="Skip cold start test (faster but less complete)",
    )
    parser.add_argument(
        "--skip-warm",
        action="store_true",
        help="Skip warm tests",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("CHAT ENDPOINT LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Scenario ID: {args.scenario_id}")
    print(f"Warm iterations: {args.warm_iterations}")
    
    cold_results = {}
    warm_results = {}
    
    if not args.skip_cold:
        cold_results = run_cold_start_test(scenario_id=args.scenario_id)
    
    if not args.skip_warm:
        warm_results = await run_warm_test(
            iterations=args.warm_iterations,
            scenario_id=args.scenario_id,
        )
    
    if cold_results or warm_results:
        print_report(cold_results, warm_results)


if __name__ == "__main__":
    asyncio.run(main())
