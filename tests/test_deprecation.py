import warnings

from src.memos.deprecation import (
    deprecated,
    deprecated_class,
    deprecated_parameter,
    get_deprecation_info,
    is_deprecated,
    warn_deprecated,
)


class TestDeprecated:
    """Test the @deprecated decorator"""

    def test_deprecated_function_warns(self):
        """Test that deprecated function issues warning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @deprecated(reason="Test reason", version="1.0.0", alternative="new_func")
            def old_func():
                return "result"

            result = old_func()

            assert result == "result"
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "old_func" in str(w[0].message)
            assert "Test reason" in str(w[0].message)
            assert "1.0.0" in str(w[0].message)
            assert "new_func" in str(w[0].message)

    def test_deprecated_function_metadata(self):
        """Test that deprecated function has correct metadata"""

        @deprecated(reason="Test", version="1.0.0", alternative="new_func")
        def old_func():
            return "result"

        assert is_deprecated(old_func)
        info = get_deprecation_info(old_func)
        assert info["reason"] == "Test"
        assert info["version"] == "1.0.0"
        assert info["alternative"] == "new_func"

    def test_deprecated_minimal(self):
        """Test deprecated decorator with minimal parameters"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @deprecated()
            def old_func():
                return "result"

            result = old_func()

            assert result == "result"
            assert len(w) == 1
            assert "old_func" in str(w[0].message)


class TestDeprecatedClass:
    """Test the @deprecated_class decorator"""

    def test_deprecated_class_warns(self):
        """Test that deprecated class issues warning on instantiation"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @deprecated_class(reason="Test reason", version="1.0.0", alternative="NewClass")
            class OldClass:
                def __init__(self, value):
                    self.value = value

            obj = OldClass("test")

            assert obj.value == "test"
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "OldClass" in str(w[0].message)
            assert "Test reason" in str(w[0].message)

    def test_deprecated_class_metadata(self):
        """Test that deprecated class has correct metadata"""

        @deprecated_class(reason="Test", version="1.0.0")
        class OldClass:
            pass

        assert is_deprecated(OldClass)
        info = get_deprecation_info(OldClass)
        assert info["reason"] == "Test"
        assert info["version"] == "1.0.0"


class TestDeprecatedParameter:
    """Test the @deprecated_parameter decorator"""

    def test_deprecated_parameter_warns(self):
        """Test that deprecated parameter issues warning when used"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            @deprecated_parameter("old_param", alternative="new_param", version="1.0.0")
            def test_func(new_param=None, old_param=None):
                return new_param or old_param

            # Using new parameter should not warn
            result1 = test_func(new_param="new_value")
            assert result1 == "new_value"
            assert len(w) == 0

            # Using old parameter should warn
            result2 = test_func(old_param="old_value")
            assert result2 == "old_value"
            assert len(w) == 1
            assert "old_param" in str(w[0].message)
            assert "new_param" in str(w[0].message)


class TestWarnDeprecated:
    """Test the warn_deprecated function"""

    def test_warn_deprecated_basic(self):
        """Test basic deprecation warning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            warn_deprecated(
                "old_item", "function", reason="Test", version="1.0.0", alternative="new_item"
            )

            assert len(w) == 1
            assert "old_item" in str(w[0].message)
            assert "Test" in str(w[0].message)
            assert "1.0.0" in str(w[0].message)
            assert "new_item" in str(w[0].message)

    def test_warn_deprecated_minimal(self):
        """Test deprecation warning with minimal parameters"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            warn_deprecated("old_item")

            assert len(w) == 1
            assert "old_item" in str(w[0].message)


class TestDeprecationUtilities:
    """Test utility functions"""

    def test_is_deprecated_false(self):
        """Test is_deprecated returns False for non-deprecated items"""

        def normal_func():
            pass

        class NormalClass:
            pass

        assert not is_deprecated(normal_func)
        assert not is_deprecated(NormalClass)
        assert not is_deprecated("string")

    def test_get_deprecation_info_none(self):
        """Test get_deprecation_info returns None for non-deprecated items"""

        def normal_func():
            pass

        assert get_deprecation_info(normal_func) is None
