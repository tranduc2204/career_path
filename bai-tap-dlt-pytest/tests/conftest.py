"""Fixture dùng chung (đã cho sẵn). Bạn viết test trong tests/test_*.py."""
import pytest

from fake_api.server import FakeApi


@pytest.fixture
def api():
    """API giả lập chạy trên cổng ngẫu nhiên, mỗi test một API mới (ngày 0, không flaky)."""
    server = FakeApi().start()
    yield server
    server.stop()


@pytest.fixture
def workdir(tmp_path):
    """Thư mục tạm cho mỗi test: chứa mayshop.duckdb và state của dlt."""
    return tmp_path
