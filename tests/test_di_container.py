import pytest
from dart_planner.common.di_container_v2 import DIContainerV2

class Dummy:
    pass

class Dummy2:
    pass

def test_finalize_prevents_registration():
    container = DIContainerV2()
    container.register_singleton(Dummy, Dummy)
    container.finalize()
    with pytest.raises(RuntimeError):
        container.register_singleton(Dummy2, Dummy2)
    with pytest.raises(RuntimeError):
        container.register_factory(Dummy2, lambda: Dummy2())
    with pytest.raises(RuntimeError):
        container.register_instance(Dummy2, Dummy2()) 