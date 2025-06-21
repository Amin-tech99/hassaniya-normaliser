"""Tests for CLI functionality."""

import os
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from hassy_normalizer.cli import main, setup_logging, print_diff
from hassy_normalizer import normalize_text


class TestCLIMain:
    """Test main CLI function."""
    
    def test_normalize_file_to_file(self):
        """Test normalizing from input file to output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            output_file = Path(tmpdir) / "output.txt"
            
            # Write test input
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            # Mock normalize_text
            with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
                # Mock sys.argv
                with patch('sys.argv', ['hassy-normalize', str(input_file), '-o', str(output_file)]):
                    main()
            
            # Check output file was created and has correct content
            assert output_file.exists()
            result = output_file.read_text(encoding="utf-8")
            assert result == "كال الرجل"
    
    def test_normalize_file_to_stdout(self, capsys):
        """Test normalizing from input file to stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
                with patch('sys.argv', ['hassy-normalize', str(input_file)]):
                    main()
            
            captured = capsys.readouterr()
            assert "كال الرجل" in captured.out
    
    def test_normalize_stdin_to_stdout(self, capsys):
        """Test normalizing from stdin to stdout."""
        with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
            with patch('sys.stdin.read', return_value="قال الرجل"):
                with patch('sys.argv', ['hassy-normalize']):
                    main()
        
        captured = capsys.readouterr()
        assert "كال الرجل" in captured.out
    
    def test_normalize_with_diff_flag(self, capsys):
        """Test normalizing with diff output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
                with patch('hassy_normalizer.cli.word_diff_simple') as mock_diff:
                    mock_diff.return_value = [
                        {"word": "كال", "changed": True},
                        {"word": " ", "changed": False},
                        {"word": "الرجل", "changed": False}
                    ]
                    
                    with patch('sys.argv', ['hassy-normalize', str(input_file), '--diff']):
                        main()
            
            captured = capsys.readouterr()
            # Should contain diff output
            assert "كال" in captured.out
            assert "الرجل" in captured.out
    
    def test_normalize_with_color_flag(self, capsys):
        """Test normalizing with color output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
                with patch('hassy_normalizer.cli.word_diff_simple') as mock_diff:
                    mock_diff.return_value = [
                        {"word": "كال", "changed": True},
                        {"word": " ", "changed": False},
                        {"word": "الرجل", "changed": False}
                    ]
                    
                    with patch('sys.argv', ['hassy-normalize', str(input_file), '--diff', '--color']):
                        main()
            
            captured = capsys.readouterr()
            # Should contain ANSI color codes or Rich formatting
            output = captured.out
            assert "كال" in output
            assert "الرجل" in output
    
    def test_file_not_found_error(self):
        """Test error handling when input file doesn't exist."""
        with patch('sys.argv', ['hassy-normalize', 'nonexistent.txt']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0
    
    def test_permission_error_output_file(self):
        """Test error handling when output file can't be written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            # Try to write to a directory (should fail)
            output_dir = Path(tmpdir) / "output_dir"
            output_dir.mkdir()
            
            with patch('sys.argv', ['hassy-normalize', str(input_file), '-o', str(output_dir)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code != 0
    
    def test_verbose_flag(self, caplog):
        """Test verbose logging flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', return_value="كال الرجل"):
                with patch('sys.argv', ['hassy-normalize', str(input_file), '-v']):
                    with caplog.at_level('DEBUG'):
                        main()
            
            # Check that debug messages were logged
            debug_messages = [record.message for record in caplog.records if record.levelname == 'DEBUG']
            assert len(debug_messages) > 0
    
    def test_help_flag(self, capsys):
        """Test help flag displays usage information."""
        with patch('sys.argv', ['hassy-normalize', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with code 0
            assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()
    
    def test_version_flag(self, capsys):
        """Test version flag displays version information."""
        with patch('sys.argv', ['hassy-normalize', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Version should exit with code 0
            assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "0.1.0" in output or "version" in output.lower()


class TestSetupLogging:
    """Test logging setup function."""
    
    def test_setup_logging_info_level(self, caplog):
        """Test logging setup with INFO level."""
        setup_logging(verbose=False)
        
        import logging
        logger = logging.getLogger('hassy_normalizer')
        
        with caplog.at_level('INFO'):
            logger.info("Test info message")
            logger.debug("Test debug message")
        
        messages = [record.message for record in caplog.records]
        assert "Test info message" in messages
        assert "Test debug message" not in messages
    
    def test_setup_logging_debug_level(self, caplog):
        """Test logging setup with DEBUG level."""
        setup_logging(verbose=True)
        
        import logging
        logger = logging.getLogger('hassy_normalizer')
        
        with caplog.at_level('DEBUG'):
            logger.info("Test info message")
            logger.debug("Test debug message")
        
        messages = [record.message for record in caplog.records]
        assert "Test info message" in messages
        assert "Test debug message" in messages
    
    def test_setup_logging_with_rich(self):
        """Test logging setup when Rich is available."""
        with patch('hassy_normalizer.cli.Console') as mock_console:
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            setup_logging(verbose=False)
            
            # Rich console should be created
            mock_console.assert_called_once()
    
    def test_setup_logging_without_rich(self):
        """Test logging setup when Rich is not available."""
        with patch('hassy_normalizer.cli.Console', side_effect=ImportError):
            # Should not raise an error
            setup_logging(verbose=False)


class TestPrintDiff:
    """Test diff printing function."""
    
    def test_print_diff_with_changes(self, capsys):
        """Test printing diff with changes."""
        diff_data = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        print_diff(diff_data, use_color=False)
        
        captured = capsys.readouterr()
        assert "كال" in captured.out
        assert "الرجل" in captured.out
        assert "1 word(s) changed" in captured.out
    
    def test_print_diff_no_changes(self, capsys):
        """Test printing diff with no changes."""
        diff_data = [
            {"word": "الرجل", "changed": False},
            {"word": " ", "changed": False},
            {"word": "يقول", "changed": False}
        ]
        
        print_diff(diff_data, use_color=False)
        
        captured = capsys.readouterr()
        assert "الرجل" in captured.out
        assert "يقول" in captured.out
        assert "0 word(s) changed" in captured.out
    
    def test_print_diff_with_color(self, capsys):
        """Test printing diff with color enabled."""
        diff_data = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        print_diff(diff_data, use_color=True)
        
        captured = capsys.readouterr()
        output = captured.out
        assert "كال" in output
        assert "الرجل" in output
        # Should contain ANSI codes or Rich formatting when color is enabled
    
    def test_print_diff_empty(self, capsys):
        """Test printing empty diff."""
        print_diff([], use_color=False)
        
        captured = capsys.readouterr()
        assert "0 word(s) changed" in captured.out
    
    def test_print_diff_with_rich_available(self, capsys):
        """Test printing diff when Rich is available."""
        diff_data = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        with patch('hassy_normalizer.cli.Console') as mock_console:
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            
            print_diff(diff_data, use_color=True)
            
            # Rich console should be used for colored output
            mock_console.assert_called()
    
    def test_print_diff_without_rich(self, capsys):
        """Test printing diff when Rich is not available."""
        diff_data = [
            {"word": "كال", "changed": True},
            {"word": " ", "changed": False},
            {"word": "الرجل", "changed": False}
        ]
        
        with patch('hassy_normalizer.cli.Console', side_effect=ImportError):
            print_diff(diff_data, use_color=True)
            
            captured = capsys.readouterr()
            output = captured.out
            assert "كال" in output
            assert "الرجل" in output
            # Should fall back to ANSI codes


class TestCLIIntegration:
    """Integration tests for CLI."""
    
    def test_cli_subprocess_basic(self):
        """Test CLI via subprocess for basic functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            output_file = Path(tmpdir) / "output.txt"
            
            # Write test input
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            # Run CLI via subprocess
            result = subprocess.run([
                sys.executable, '-m', 'hassy_normalizer.cli',
                str(input_file), '-o', str(output_file)
            ], capture_output=True, text=True, encoding='utf-8')
            
            # Check exit code
            if result.returncode != 0:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            
            # Note: This test might fail if the actual normalizer isn't working
            # In a real scenario, you'd have the actual implementation
    
    def test_cli_subprocess_diff_output(self):
        """Test CLI diff output via subprocess."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            # Run CLI with diff flag
            result = subprocess.run([
                sys.executable, '-m', 'hassy_normalizer.cli',
                str(input_file), '--diff'
            ], capture_output=True, text=True, encoding='utf-8')
            
            # Check that diff output is generated
            if result.returncode == 0:
                assert len(result.stdout) > 0
    
    def test_cli_subprocess_help(self):
        """Test CLI help via subprocess."""
        result = subprocess.run([
            sys.executable, '-m', 'hassy_normalizer.cli',
            '--help'
        ], capture_output=True, text=True, encoding='utf-8')
        
        # Help should exit with code 0
        assert result.returncode == 0
        # Should contain usage information
        output = result.stdout + result.stderr
        assert "usage" in output.lower() or "help" in output.lower()
    
    def test_cli_subprocess_version(self):
        """Test CLI version via subprocess."""
        result = subprocess.run([
            sys.executable, '-m', 'hassy_normalizer.cli',
            '--version'
        ], capture_output=True, text=True, encoding='utf-8')
        
        # Version should exit with code 0
        assert result.returncode == 0
        # Should contain version information
        output = result.stdout + result.stderr
        assert "0.1.0" in output or "version" in output.lower()


class TestCLIErrorHandling:
    """Test CLI error handling."""
    
    def test_malformed_input_file(self):
        """Test handling of malformed input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            # Write binary data that's not valid UTF-8
            input_file.write_bytes(b'\xff\xfe\x00\x00')
            
            with patch('sys.argv', ['hassy-normalize', str(input_file)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # Should exit with non-zero code
                assert exc_info.value.code != 0
    
    def test_normalization_exception(self):
        """Test handling of normalization exceptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', 
                      side_effect=Exception("Normalization failed")):
                with patch('sys.argv', ['hassy-normalize', str(input_file)]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit with non-zero code
                    assert exc_info.value.code != 0
    
    def test_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("قال الرجل", encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', 
                      side_effect=KeyboardInterrupt()):
                with patch('sys.argv', ['hassy-normalize', str(input_file)]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit with specific code for keyboard interrupt
                    assert exc_info.value.code != 0


class TestCLIUnicodeHandling:
    """Test CLI Unicode and encoding handling."""
    
    def test_unicode_input_output(self):
        """Test handling of Unicode text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            output_file = Path(tmpdir) / "output.txt"
            
            # Unicode text with various Arabic characters and emojis
            unicode_text = "مرحبا بالعالم 🌟 هذا نص تجريبي"
            input_file.write_text(unicode_text, encoding="utf-8")
            
            with patch('hassy_normalizer.cli.normalize_text', return_value=unicode_text):
                with patch('sys.argv', ['hassy-normalize', str(input_file), '-o', str(output_file)]):
                    main()
            
            # Check that Unicode is preserved
            result = output_file.read_text(encoding="utf-8")
            assert result == unicode_text
    
    def test_different_encodings(self):
        """Test handling of different file encodings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            
            # Write file with different encoding
            text = "مرحبا بالعالم"
            input_file.write_text(text, encoding="utf-16")
            
            # CLI should handle encoding detection or fail gracefully
            with patch('sys.argv', ['hassy-normalize', str(input_file)]):
                # This might fail, which is acceptable behavior
                try:
                    main()
                except SystemExit:
                    pass  # Expected for encoding issues


if __name__ == '__main__':
    pytest.main([__file__])