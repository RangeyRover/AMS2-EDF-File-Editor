import pytest
from unittest.mock import MagicMock, patch
from src.utils.plotting import plot_torque_rpm, plot_compression_rpm, plot_both
from src.core.parser import parse_torque_tables

@patch('src.utils.plotting._ensure_matplotlib')
def test_plot_torque_rpm(mock_ensure, synthetic_torque_data):
    # Mock plt
    mock_plt = MagicMock()
    mock_ensure.return_value = mock_plt
    
    tables = parse_torque_tables(synthetic_torque_data)
    
    # Configure mock to return a figure and axis
    mock_fig = MagicMock()
    mock_ax1 = MagicMock()
    mock_ax2 = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax1)
    mock_ax1.twinx.return_value = mock_ax2
    
    # Mock legend handles
    mock_ax1.get_legend_handles_labels.return_value = ([], [])
    mock_ax2.get_legend_handles_labels.return_value = ([], [])
    
    print("\nDEBUG: Calling plot_torque_rpm")
    # Run
    plot_torque_rpm(tables, "test.edf")
    print("DEBUG: Returned from plot_torque_rpm")
    
    # Verify subplots called
    mock_plt.subplots.assert_called_once()
    
    # Verify plot called on ax1 (Torque)
    # Using call_args[0] (args) and call_args[1] (kwargs) is safer
    call_args = mock_ax1.plot.call_args
    assert call_args is not None, "ax1.plot was not called"
    
    args = call_args[0]
    # kwargs = call_args[1]
    
    rpms = args[0]
    torques = args[1]
    
    assert rpms == [0.0, 1000.0, 2000.5]
    assert torques == [100.0, 150.0, 200.0]
    
    # Verify plot called on ax2 (Power)
    call_args_p = mock_ax2.plot.call_args
    assert call_args_p is not None, "ax2.plot was not called"
    
    args_p = call_args_p[0]
    powers = args_p[1]
    
    assert powers[0] == 0.0
    assert powers[1] == pytest.approx(15.7079, 0.0001)

@patch('src.utils.plotting._ensure_matplotlib')
def test_plot_compression_rpm(mock_ensure, synthetic_torque_data):
    mock_plt = MagicMock()
    mock_ensure.return_value = mock_plt
    
    tables = parse_torque_tables(synthetic_torque_data)
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)
    
    plot_compression_rpm(tables)
    
    mock_ax.plot.assert_called()
    args = mock_ax.plot.call_args[0]
    comps = args[1]
    # All rows have 10.0 compression
    assert comps == [10.0, 10.0, 10.0]

def test_plot_missing_matplotlib(synthetic_torque_data):
    # Simulate ImportError
    # We must pass tables to bypass the 'not tables' check
    tables = parse_torque_tables(synthetic_torque_data)
    with patch('src.utils.plotting._ensure_matplotlib', side_effect=ImportError("No mpl")):
        with pytest.raises(ImportError):
            plot_torque_rpm(tables, "file")
