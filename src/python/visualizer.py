"""
Visualization utilities for benchmark results.
Generate performance comparison charts and component breakdowns.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any


# Configure fonts (includes fallback for Chinese if available)
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_results(path: str) -> dict:
    """Load benchmark results JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_setup_breakdown(results: dict, output_dir: str = "./results/figures"):
    """
    Generate a breakdown chart for the Setup phase.
    Shows time shares for encryption upload, secure K-Means, and secure HNSW build.
    """
    setup_data = results.get('setup', [])
    if not setup_data:
        print("[Visualizer] No setup data found")
        return
    
    components = []
    times = []
    for item in setup_data:
        components.append(f"{item['component']}\n({item['operation']})")
        times.append(item['total_time'])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Bar chart
    colors = ['#3498db', '#e74c3c', '#2ecc71']
    bars = axes[0].bar(components, times, color=colors[:len(components)])
    axes[0].set_ylabel('Time (seconds)', fontsize=12)
    axes[0].set_title('Setup Phase - Component Breakdown', fontsize=14, fontweight='bold')
    axes[0].tick_params(axis='x', rotation=0)
    
    # Add numeric labels
    for bar, t in zip(bars, times):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f'{t:.3f}s', ha='center', va='bottom', fontsize=10)
    
    # Pie chart
    axes[1].pie(times, labels=components, autopct='%1.1f%%', colors=colors[:len(components)],
                startangle=90, explode=[0.02]*len(times))
    axes[1].set_title('Setup Phase - Time Distribution', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'setup_breakdown.png'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_retrieval_latency(results: dict, output_dir: str = "./results/figures"):
    """
    Generate retrieval latency analysis plot.
    Shows latency for different top-K values.
    """
    retrieve_data = results.get('retrieve', [])
    if not retrieve_data:
        print("[Visualizer] No retrieve data found")
        return
    
    # Filter search results
    search_results = [r for r in retrieve_data if 'search_top' in r['operation']]
    if not search_results:
        print("[Visualizer] No search results found")
        return
    
    top_k_values = []
    avg_times = []
    for r in search_results:
        k = int(r['operation'].replace('search_top', ''))
        top_k_values.append(k)
        avg_times.append(r['avg_time_per_item'] * 1000)  # convert to milliseconds
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(top_k_values, avg_times, 'o-', linewidth=2, markersize=10, 
            color='#9b59b6', label='Secure HNSW Search')
    ax.fill_between(top_k_values, avg_times, alpha=0.3, color='#9b59b6')
    
    ax.set_xlabel('Top-K Value', fontsize=12)
    ax.set_ylabel('Average Latency (ms)', fontsize=12)
    ax.set_title('Retrieval Latency vs Top-K', fontsize=14, fontweight='bold')
    ax.set_xticks(top_k_values)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    
    # Add data point labels
    for k, t in zip(top_k_values, avg_times):
        ax.annotate(f'{t:.2f}ms', (k, t), textcoords="offset points", 
                    xytext=(0, 10), ha='center', fontsize=9)
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'retrieval_latency_vs_topk.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_update_throughput(results: dict, output_dir: str = "./results/figures"):
    """
    Generate update throughput plot.
    Shows insert/delete performance for different batch sizes.
    """
    update_data = results.get('update', [])
    if not update_data:
        print("[Visualizer] No update data found")
        return
    
    # Separate insert and delete records
    insert_data = [r for r in update_data if 'insert' in r['operation']]
    delete_data = [r for r in update_data if 'delete' in r['operation']]
    
    if not insert_data:
        print("[Visualizer] No insert/delete data found")
        return
    
    batch_sizes = [r['num_items'] for r in insert_data]
    insert_times = [r['avg_time_per_item'] * 1000 for r in insert_data]  # ms
    delete_times = [r['avg_time_per_item'] * 1000 for r in delete_data] if delete_data else [0]*len(batch_sizes)
    
    x = np.arange(len(batch_sizes))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, insert_times, width, label='Secure Insert', color='#3498db')
    bars2 = ax.bar(x + width/2, delete_times, width, label='Secure Delete', color='#e74c3c')
    
    ax.set_xlabel('Batch Size', fontsize=12)
    ax.set_ylabel('Average Time per Vector (ms)', fontsize=12)
    ax.set_title('Update Throughput by Batch Size', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([str(b) for b in batch_sizes])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add numeric labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'update_throughput.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_component_details(results: dict, output_dir: str = "./results/figures"):
    """
    Generate detailed component breakdowns.
    Shows internal timing for K-Means and HNSW stages.
    """
    setup_data = results.get('setup', [])
    
    # Locate K-Means and HNSW detail entries
    kmeans_result = next((r for r in setup_data if r['component'] == 'secure_kmeans'), None)
    hnsw_result = next((r for r in setup_data if r['component'] == 'secure_hnsw'), None)
    
    if not kmeans_result or not kmeans_result.get('details'):
        print("[Visualizer] No K-Means details found")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # K-Means internal breakdown
    km_details = kmeans_result['details']
    km_labels = list(km_details.keys())
    km_values = list(km_details.values())
    
    colors_km = ['#1abc9c', '#f39c12', '#e74c3c', '#9b59b6']
    axes[0].barh(km_labels, km_values, color=colors_km[:len(km_labels)])
    axes[0].set_xlabel('Time (seconds)', fontsize=12)
    axes[0].set_title('Secure K-Means - Internal Breakdown', fontsize=14, fontweight='bold')
    for i, v in enumerate(km_values):
        axes[0].text(v + 0.001, i, f'{v:.4f}s', va='center', fontsize=10)
    
    # HNSW internal breakdown
    if hnsw_result and hnsw_result.get('details'):
        hnsw_details = hnsw_result['details']
        hnsw_labels = list(hnsw_details.keys())
        hnsw_values = list(hnsw_details.values())
        
        colors_hnsw = ['#3498db', '#2ecc71', '#e67e22']
        axes[1].barh(hnsw_labels, hnsw_values, color=colors_hnsw[:len(hnsw_labels)])
        axes[1].set_xlabel('Time (seconds)', fontsize=12)
        axes[1].set_title('Secure HNSW Build - Internal Breakdown', fontsize=14, fontweight='bold')
        for i, v in enumerate(hnsw_values):
            axes[1].text(v + 0.001, i, f'{v:.4f}s', va='center', fontsize=10)
    else:
        axes[1].text(0.5, 0.5, 'No HNSW details available', 
                     ha='center', va='center', transform=axes[1].transAxes)
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'component_details.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def generate_all_figures(
    results_path: str = "./results/timings.json",
    output_dir: str = "./results/figures"
):
    """Generate all visualization figures from a timings JSON file."""
    print("\n" + "="*60)
    print("Generating Visualization Figures")
    print("="*60)
    
    results = load_results(results_path)
    
    plot_setup_breakdown(results, output_dir)
    plot_retrieval_latency(results, output_dir)
    plot_update_throughput(results, output_dir)
    plot_component_details(results, output_dir)
    
    print("\n[Visualizer] All figures generated successfully!")
    print(f"[Visualizer] Output directory: {output_dir}")


def plot_scale_setup_comparison(results: dict, output_dir: str = "./results/figures"):
    """Generate multi-scale Setup phase comparison plots."""
    scales_data = results.get('scales', {})
    if not scales_data:
        print("[Visualizer] No multi-scale data found")
        return
    
    scale_names = []
    setup_times = []
    component_breakdown = {'encryption': [], 'kmeans': [], 'hnsw': []}
    
    for scale_name in ['100k', '1m', '10m']:
        if scale_name not in scales_data:
            continue
        scale_data = scales_data[scale_name]
        setup_data = scale_data.get('setup', [])
        
        scale_names.append(scale_name.upper())
        total_time = sum(r['total_time'] for r in setup_data)
        setup_times.append(total_time)
        
        # Break down per-component times
        for r in setup_data:
            if 'encryption' in r['component'] or 'encryption' in r['operation']:
                component_breakdown['encryption'].append(r['total_time'])
            elif 'kmeans' in r['component']:
                component_breakdown['kmeans'].append(r['total_time'])
            elif 'hnsw' in r['component']:
                component_breakdown['hnsw'].append(r['total_time'])
    
    if not scale_names:
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Total Setup time comparison (log scale)
    x = np.arange(len(scale_names))
    bars = axes[0].bar(x, setup_times, color=['#3498db', '#e74c3c', '#2ecc71'][:len(scale_names)])
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(scale_names)
    axes[0].set_ylabel('Time (seconds)', fontsize=12)
    axes[0].set_title('Setup Time by Data Scale', fontsize=14, fontweight='bold')
    axes[0].set_yscale('log')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    for bar, t in zip(bars, setup_times):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1,
                     f'{t:.2f}s', ha='center', va='bottom', fontsize=10)
    
    # Stacked bar chart showing component breakdown
    width = 0.5
    bottom = np.zeros(len(scale_names))
    colors = {'encryption': '#3498db', 'kmeans': '#e74c3c', 'hnsw': '#2ecc71'}
    labels = {'encryption': 'Encryption', 'kmeans': 'Secure K-Means', 'hnsw': 'Secure HNSW'}
    
    for comp_name, times in component_breakdown.items():
        if times and len(times) == len(scale_names):
            axes[1].bar(x, times, width, bottom=bottom, label=labels[comp_name], 
                       color=colors[comp_name])
            bottom += np.array(times)
    
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(scale_names)
    axes[1].set_ylabel('Time (seconds)', fontsize=12)
    axes[1].set_title('Setup Time Breakdown by Scale', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'scale_setup_comparison.png'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_scale_retrieval_comparison(results: dict, output_dir: str = "./results/figures"):
    """Generate retrieval-latency comparison across multiple data scales."""
    scales_data = results.get('scales', {})
    if not scales_data:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = {'100k': '#3498db', '1m': '#e74c3c', '10m': '#2ecc71'}
    markers = {'100k': 'o', '1m': 's', '10m': '^'}
    
    for scale_name in ['100k', '1m', '10m']:
        if scale_name not in scales_data:
            continue
        scale_data = scales_data[scale_name]
        retrieve_data = scale_data.get('retrieve', [])
        search_results = [r for r in retrieve_data if 'search_top' in r['operation']]
        
        if not search_results:
            continue
        
        top_k_values = []
        avg_times = []
        for r in search_results:
            k = int(r['operation'].replace('search_top', ''))
            top_k_values.append(k)
            avg_times.append(r['avg_time_per_item'] * 1000)
        
        ax.plot(top_k_values, avg_times, f'{markers[scale_name]}-', 
                linewidth=2, markersize=8, color=colors[scale_name],
                label=f'{scale_name.upper()} vectors')
    
    ax.set_xlabel('Top-K Value', fontsize=12)
    ax.set_ylabel('Average Latency (ms)', fontsize=12)
    ax.set_title('Retrieval Latency Comparison Across Scales', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'scale_retrieval_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_scale_update_comparison(results: dict, output_dir: str = "./results/figures"):
    """Generate update throughput comparison across multiple data scales."""
    scales_data = results.get('scales', {})
    if not scales_data:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scale_names = []
    insert_throughputs = []
    delete_throughputs = []
    
    for scale_name in ['100k', '1m', '10m']:
        if scale_name not in scales_data:
            continue
        scale_data = scales_data[scale_name]
        update_data = scale_data.get('update', [])
        
        # Compute average throughput
        insert_data = [r for r in update_data if 'insert' in r['operation']]
        delete_data = [r for r in update_data if 'delete' in r['operation']]
        
        if insert_data:
            scale_names.append(scale_name.upper())
            avg_insert = np.mean([r['num_items'] / r['total_time'] for r in insert_data])
            insert_throughputs.append(avg_insert)
            
            if delete_data:
                avg_delete = np.mean([r['num_items'] / r['total_time'] for r in delete_data])
                delete_throughputs.append(avg_delete)
            else:
                delete_throughputs.append(0)
    
    if not scale_names:
        return
    
    x = np.arange(len(scale_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, insert_throughputs, width, label='Insert Throughput', color='#3498db')
    bars2 = ax.bar(x + width/2, delete_throughputs, width, label='Delete Throughput', color='#e74c3c')
    
    ax.set_xlabel('Data Scale', fontsize=12)
    ax.set_ylabel('Throughput (vectors/sec)', fontsize=12)
    ax.set_title('Update Throughput Comparison Across Scales', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(scale_names)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'scale_update_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def plot_scalability_analysis(results: dict, output_dir: str = "./results/figures"):
    """Generate scalability analysis plots (log-log and semilog axes)."""
    scales_data = results.get('scales', {})
    if not scales_data:
        return
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    scale_vectors = {'100k': 100000, '1m': 1000000, '10m': 10000000}
    
    num_vectors_list = []
    setup_times = []
    retrieve_times = []
    update_times = []
    
    for scale_name in ['100k', '1m', '10m']:
        if scale_name not in scales_data:
            continue
        scale_data = scales_data[scale_name]
        
        num_vectors_list.append(scale_vectors[scale_name])
        
        # Setup time
        setup_time = sum(r['total_time'] for r in scale_data.get('setup', []))
        setup_times.append(setup_time)
        
        # Average retrieve time
        search_results = [r for r in scale_data.get('retrieve', []) if 'search' in r['operation']]
        if search_results:
            retrieve_times.append(np.mean([r['avg_time_per_item'] * 1000 for r in search_results]))
        else:
            retrieve_times.append(0)
        
        # Total update time
        update_time = sum(r['total_time'] for r in scale_data.get('update', []))
        update_times.append(update_time)
    
    if not num_vectors_list:
        return
    
    # Setup scalability
    axes[0].loglog(num_vectors_list, setup_times, 'o-', linewidth=2, markersize=10, color='#3498db')
    axes[0].set_xlabel('Number of Vectors', fontsize=11)
    axes[0].set_ylabel('Setup Time (s)', fontsize=11)
    axes[0].set_title('Setup Scalability', fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # Retrieval scalability
    axes[1].semilogx(num_vectors_list, retrieve_times, 's-', linewidth=2, markersize=10, color='#e74c3c')
    axes[1].set_xlabel('Number of Vectors', fontsize=11)
    axes[1].set_ylabel('Avg Query Latency (ms)', fontsize=11)
    axes[1].set_title('Retrieval Scalability', fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    # Update scalability
    axes[2].loglog(num_vectors_list, update_times, '^-', linewidth=2, markersize=10, color='#2ecc71')
    axes[2].set_xlabel('Number of Vectors', fontsize=11)
    axes[2].set_ylabel('Update Time (s)', fontsize=11)
    axes[2].set_title('Update Scalability', fontsize=12, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'scalability_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] Saved {output_path}")


def generate_scale_comparison_figures(
    results_path: str = "./results/multiscale_timings.json",
    output_dir: str = "./results/figures"
):
    """Generate multi-scale comparison visualizations from a JSON file."""
    print("\n" + "="*60)
    print("Generating Multi-Scale Comparison Figures")
    print("="*60)
    
    results = load_results(results_path)
    
    plot_scale_setup_comparison(results, output_dir)
    plot_scale_retrieval_comparison(results, output_dir)
    plot_scale_update_comparison(results, output_dir)
    plot_scalability_analysis(results, output_dir)
    
    print("\n[Visualizer] Scale comparison figures generated successfully!")
    print(f"[Visualizer] Output directory: {output_dir}")


if __name__ == "__main__":
    generate_all_figures()
