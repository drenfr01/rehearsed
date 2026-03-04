"""Unit tests for timing utilities."""

import asyncio
import time

import pytest

from app.core.timing import (
    TimingContext,
    get_current_timing,
    measure_operation,
    set_current_timing,
    timing_scope,
)


@pytest.mark.unit
class TestTimingContext:
    """Test TimingContext class."""

    def test_initialization(self):
        ctx = TimingContext(request_id="req-1")
        assert ctx.request_id == "req-1"
        assert ctx.prefix == ""
        assert ctx.timings == {}

    def test_initialization_with_prefix(self):
        ctx = TimingContext(request_id="req-1", prefix="chat")
        assert ctx.prefix == "chat"

    def test_measure_records_timing(self):
        ctx = TimingContext(request_id="req-1")
        with ctx.measure("operation"):
            time.sleep(0.01)

        assert "operation" in ctx.timings
        assert ctx.timings["operation"] >= 0.01

    def test_measure_with_prefix(self):
        ctx = TimingContext(request_id="req-1", prefix="chat")
        with ctx.measure("llm_call"):
            pass

        assert "chat.llm_call" in ctx.timings

    async def test_measure_async(self):
        ctx = TimingContext(request_id="req-1")
        async with ctx.measure_async("async_op"):
            await asyncio.sleep(0.01)

        assert "async_op" in ctx.timings
        assert ctx.timings["async_op"] >= 0.01

    def test_record_manual(self):
        ctx = TimingContext(request_id="req-1")
        ctx.record("manual_op", 1.5)

        assert ctx.timings["manual_op"] == 1.5

    def test_get_duration(self):
        ctx = TimingContext(request_id="req-1")
        ctx.record("operation", 0.5)

        assert ctx.get_duration("operation") == 0.5

    def test_get_duration_nonexistent(self):
        ctx = TimingContext(request_id="req-1")
        assert ctx.get_duration("nonexistent") is None

    def test_get_duration_with_prefix(self):
        ctx = TimingContext(request_id="req-1", prefix="chat")
        ctx.record("op", 0.3)

        assert ctx.get_duration("op") == 0.3

    def test_log_summary(self):
        """Test that log_summary runs without error."""
        ctx = TimingContext(request_id="req-1")
        ctx.record("op1", 0.5)
        ctx.record("op2", 0.3)
        ctx.log_summary()

    def test_multiple_measurements(self):
        ctx = TimingContext(request_id="req-1")
        with ctx.measure("op1"):
            pass
        with ctx.measure("op2"):
            pass

        assert "op1" in ctx.timings
        assert "op2" in ctx.timings


@pytest.mark.unit
class TestTimingScope:
    """Test timing_scope context manager."""

    def test_creates_and_cleans_up_context(self):
        assert get_current_timing() is None

        with timing_scope("req-1") as timing:
            assert get_current_timing() is timing
            assert timing.request_id == "req-1"

        assert get_current_timing() is None

    def test_nested_scopes(self):
        with timing_scope("outer") as outer:
            assert get_current_timing() is outer

            with timing_scope("inner") as inner:
                assert get_current_timing() is inner

            assert get_current_timing() is outer

        assert get_current_timing() is None


@pytest.mark.unit
class TestSetGetCurrentTiming:
    """Test get/set current timing context."""

    def test_default_is_none(self):
        set_current_timing(None)
        assert get_current_timing() is None

    def test_set_and_get(self):
        ctx = TimingContext(request_id="req-1")
        set_current_timing(ctx)
        assert get_current_timing() is ctx
        set_current_timing(None)


@pytest.mark.unit
class TestMeasureOperation:
    """Test measure_operation decorator."""

    def test_sync_function_with_timing(self):
        @measure_operation("test_op")
        def my_func():
            return 42

        ctx = TimingContext(request_id="req-1")
        set_current_timing(ctx)

        result = my_func()

        assert result == 42
        assert "test_op" in ctx.timings
        set_current_timing(None)

    def test_sync_function_without_timing(self):
        @measure_operation("test_op")
        def my_func():
            return 42

        set_current_timing(None)
        result = my_func()
        assert result == 42

    async def test_async_function_with_timing(self):
        @measure_operation("async_op")
        async def my_async_func():
            return 99

        ctx = TimingContext(request_id="req-1")
        set_current_timing(ctx)

        result = await my_async_func()

        assert result == 99
        assert "async_op" in ctx.timings
        set_current_timing(None)

    async def test_async_function_without_timing(self):
        @measure_operation("async_op")
        async def my_async_func():
            return 99

        set_current_timing(None)
        result = await my_async_func()
        assert result == 99
