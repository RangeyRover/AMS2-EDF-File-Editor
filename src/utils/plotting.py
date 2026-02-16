import logging
from typing import List, Optional
from pathlib import Path

from ..core.models import TorqueTable

logger = logging.getLogger(__name__)

def _ensure_matplotlib():
    """
    Attempts to import matplotlib. Raises ImportError if not found.
    """
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        logger.error("Matplotlib not found.")
        raise ImportError("matplotlib is required for plotting.\nInstall it with: pip install matplotlib")

def plot_torque_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots Torque (Nm) and Power (kW) vs RPM.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Create second y-axis for power
    ax2 = ax1.twinx()
    
    # Color schemes
    torque_colors = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']  # Blues/greens for torque
    power_colors = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']   # Orange shades for power
    
    for t_idx, table in enumerate(tables):
        rpms = []
        torques = []
        powers = []
        
        for row in table.rows:
            if row.torque is not None:  # Skip endvar rows without torque
                rpms.append(row.rpm)
                torques.append(row.torque)
                # Power (kW) = Torque (Nm) × RPM / 9549.3
                power_kw = (row.torque * row.rpm) / 9549.3
                powers.append(power_kw)
        
        if rpms:
            torque_color = torque_colors[t_idx % len(torque_colors)]
            power_color = power_colors[t_idx % len(power_colors)]
            
            # Plot torque on left axis
            ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque @ 0x{table.offset:X}', 
                            linewidth=2, markersize=4, color=torque_color)
            # Plot power on right axis (dashed line, orange shades)
            ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power @ 0x{table.offset:X}', 
                            linewidth=2, markersize=4, linestyle='--', color=power_color)
    
    ax1.set_xlabel('RPM', fontsize=12)
    ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    ax1.set_title(f'Torque & Power vs RPM - {Path(filename).name}', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
    
    plt.tight_layout()
    plt.show()

def plot_compression_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots Compression vs RPM.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for t_idx, table in enumerate(tables):
        rpms = []
        comps = []
        
        for row in table.rows:
            if row.torque is not None:
                rpms.append(row.rpm)
                comps.append(row.compression)
        
        if rpms:
            ax.plot(rpms, comps, marker='o', label=f'Table {t_idx} @ 0x{table.offset:X}', linewidth=2, markersize=4)
    
    ax.set_xlabel('RPM', fontsize=12)
    ax.set_ylabel('Compression (-Nm)', fontsize=12)
    ax.set_title(f'Compression vs RPM - {Path(filename).name}', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_both(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots both (Torque/Power vs RPM) and (Compression vs RPM) side-by-side.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Create second y-axis for power on left plot
    ax2 = ax1.twinx()
    
    # Color schemes
    torque_colors = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']
    power_colors = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']
    
    for t_idx, table in enumerate(tables):
        rpms = []
        comps = []
        torques = []
        powers = []
        
        for row in table.rows:
            if row.torque is not None:
                rpms.append(row.rpm)
                comps.append(row.compression)
                torques.append(row.torque)
                power_kw = (row.torque * row.rpm) / 9549.3
                powers.append(power_kw)
        
        if rpms:
            label = f'Table {t_idx} @ 0x{table.offset:X}'
            torque_color = torque_colors[t_idx % len(torque_colors)]
            power_color = power_colors[t_idx % len(power_colors)]
            
            # Left plot: Torque and Power
            ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque', 
                    linewidth=2, markersize=4, color=torque_color)
            ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power', 
                    linewidth=2, markersize=4, linestyle='--', color=power_color)
            # Right plot: Compression
            ax3.plot(rpms, comps, marker='o', label=label, linewidth=2, markersize=4)
    
    # Configure left plot
    ax1.set_xlabel('RPM', fontsize=12)
    ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    ax1.set_title('Torque & Power vs RPM', fontsize=13)
    ax1.grid(True, alpha=0.3)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)
    
    # Configure right plot
    ax3.set_xlabel('RPM', fontsize=12)
    ax3.set_ylabel('Compression (-Nm)', fontsize=12)
    ax3.set_title('Compression vs RPM', fontsize=13)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    fig.suptitle(f'{Path(filename).name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()
