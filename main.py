import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

from avellaneda_stoikov import AvellanedaStoikovMarketMaker
from market_data import MarketDataGenerator, HistoricalMarketDataGenerator, LOBSTERMarketDataGenerator
from market_maker import MarketMaker
from order_book import OrderBook
from simulator import Simulator


def build_synthetic_history(n_ticks, initial_price=100.0, seed=None, strategy=None):
    market_data_generator = MarketDataGenerator(initial_price=initial_price, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed, strategy=strategy)
    history = simulator.run(n_ticks)
    return history


def build_historical_history(csv_path, n_ticks, seed=None, strategy=None):
    market_data_generator = HistoricalMarketDataGenerator(csv_path, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed, strategy=strategy)
    history = simulator.run(n_ticks)
    return history


def build_lobster_history(message_csv_path, seed=None, strategy=None):
    market_data_generator = LOBSTERMarketDataGenerator(message_csv_path, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed, strategy=strategy)
    history = simulator.run_replay()
    return history


def _draw_depth(ax, depth_snapshot):
    ax.clear()
    bids = depth_snapshot['bids']
    asks = depth_snapshot['asks']

    bid_x = [-(i + 1) for i in range(len(bids))]
    ask_x = [i + 1 for i in range(len(asks))]

    ax.bar(bid_x, [qty for _, qty in bids], color='tab:green', label='Bids')
    ax.bar(ask_x, [qty for _, qty in asks], color='tab:red', label='Asks')

    for x, (price, qty) in zip(bid_x, bids):
        ax.text(x, qty, f"{price:.2f}", ha='center', va='bottom', fontsize=7)
    for x, (price, qty) in zip(ask_x, asks):
        ax.text(x, qty, f"{price:.2f}", ha='center', va='bottom', fontsize=7)

    ax.set_xticks([])
    ax.set_ylabel('Quantity')
    ax.set_title('Order Book Depth')
    ax.legend(loc='upper right')


def _mm_entry_for_step(strategy, history, step):
    if strategy is None:
        return None
    return strategy.history[history[step]['tick'] - 1]


def _fmt(value):
    return "N/A" if value is None else f"{value:.2f}"


def _build_stats_text(step, history, strategy):
    entry = history[step]
    lines = [
        f"Reference: {_fmt(entry['reference_price'])}",
        f"Mid: {_fmt(entry['mid_price'])}",
        f"Best Bid: {_fmt(entry['best_bid'])}",
        f"Best Ask: {_fmt(entry['best_ask'])}",
    ]
    mm_entry = _mm_entry_for_step(strategy, history, step)
    if mm_entry is not None:
        lines += [
            "",
            f"MM Bid: {_fmt(mm_entry['bid_price'])}",
            f"MM Ask: {_fmt(mm_entry['ask_price'])}",
            f"MM Inventory: {mm_entry['inventory']}",
            f"MM Cash: {_fmt(mm_entry['cash'])}",
        ]
    return "\n".join(lines)


def show_interactive(history, strategy=None, title="Simulation", max_price_points=3000):
    # Real replays (e.g. LOBSTER) carry a real timestamp per entry; synthetic/
    # historical runs don't, so fall back to the step index as the x-axis.
    x = [entry.get('timestamp') if entry.get('timestamp') is not None else i
         for i, entry in enumerate(history)]
    x_label = 'Time (seconds after midnight)' if history[0].get('timestamp') is not None else 'Step'
    reference_prices = [entry['reference_price'] if entry['reference_price'] is not None else float('nan') for entry in history]
    mid_prices = [entry['mid_price'] if entry['mid_price'] is not None else float('nan') for entry in history]
    best_bids = [entry['best_bid'] if entry['best_bid'] is not None else float('nan') for entry in history]
    best_asks = [entry['best_ask'] if entry['best_ask'] is not None else float('nan') for entry in history]

    if strategy is not None:
        mm_bids = [_mm_entry_for_step(strategy, history, i)['bid_price'] for i in range(len(history))]
        mm_asks = [_mm_entry_for_step(strategy, history, i)['ask_price'] for i in range(len(history))]
        mm_bids = [v if v is not None else float('nan') for v in mm_bids]
        mm_asks = [v if v is not None else float('nan') for v in mm_asks]

    # Downsample what actually gets plotted so that the interactive plot doesn't get bogged down with thousands of points
    stride = max(1, len(history) // max_price_points)
    x_plot = x[::stride]
    reference_prices_plot = reference_prices[::stride]
    mid_prices_plot = mid_prices[::stride]
    best_bids_plot = best_bids[::stride]
    best_asks_plot = best_asks[::stride]

    fig, (ax_price, ax_depth) = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title(title)
    plt.subplots_adjust(bottom=0.2, hspace=0.4)

    ax_price.plot(x_plot, reference_prices_plot, label='Reference Price', color='blue')
    ax_price.plot(x_plot, mid_prices_plot, label='Mid Price', color='green')
    ax_price.plot(x_plot, best_bids_plot, label='Best Bid', color='orange')
    ax_price.plot(x_plot, best_asks_plot, label='Best Ask', color='red')
    if strategy is not None:
        ax_price.plot(x_plot, mm_bids[::stride], label='MM Bid', color='darkgreen', linestyle='--')
        ax_price.plot(x_plot, mm_asks[::stride], label='MM Ask', color='darkred', linestyle='--')
    ax_price.set_xlabel(x_label)
    ax_price.set_ylabel('Price')
    ax_price.set_title('Price Evolution Over Time')
    ax_price.legend(loc='upper left')

    current_marker = ax_price.axvline(x=x[0], color='black', linestyle='--')

    stats_text = ax_price.text(
        0.99, 0.98, _build_stats_text(0, history, strategy),
        transform=ax_price.transAxes, ha='right', va='top', fontsize=8,
        family='monospace', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
    )

    _draw_depth(ax_depth, history[0]['depth_snapshot'])

    slider_ax = fig.add_axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(slider_ax, 'Step', valmin=0, valmax=len(history) - 1, valinit=0, valstep=1)

    fig.canvas.draw()
    price_background = fig.canvas.copy_from_bbox(ax_price.bbox)

    def on_slider_change(val):
        step = int(slider.val)

        fig.canvas.restore_region(price_background)
        current_marker.set_xdata([x[step], x[step]])
        stats_text.set_text(_build_stats_text(step, history, strategy))
        ax_price.draw_artist(current_marker)
        ax_price.draw_artist(stats_text)
        fig.canvas.blit(ax_price.bbox)

        _draw_depth(ax_depth, history[step]['depth_snapshot'])
        ax_depth.draw_artist(ax_depth.patch)
        for artist in ax_depth.get_children():
            ax_depth.draw_artist(artist)
        fig.canvas.blit(ax_depth.bbox)

    slider.on_changed(on_slider_change)

    plt.show()


if __name__ == "__main__":
    # A fresh MarketMaker per run -- sharing one instance across runs would
    # carry inventory/cash/history over from the previous sim's OrderBook,
    # corrupting both the PnL numbers and the per-tick history indexing.
    synthetic_market_maker = MarketMaker(half_spread=0.25, skew_coefficient=0.01, quote_size=20)
    synthetic_history = build_synthetic_history(n_ticks=400, seed=42, strategy=synthetic_market_maker)
    show_interactive(synthetic_history, strategy=synthetic_market_maker, title="Synthetic Data Simulation (with Market Maker)")

    avellaneda_market_maker = AvellanedaStoikovMarketMaker(gamma=1e-4, sigma=0.5, k=20, terminal_time=400, quote_size=20, max_inventory=100)
    avellaneda_history = build_synthetic_history(n_ticks=400, seed=42, strategy=avellaneda_market_maker)
    show_interactive(avellaneda_history, strategy=avellaneda_market_maker, title="Synthetic Data Simulation (with Avellaneda-Stoikov Market Maker)")

    historical_history = build_historical_history("data/AAPL_1m.csv", n_ticks=400, seed=42)
    show_interactive(historical_history, title="Historical Data Simulation (AAPL, 1m)")

    lobster_market_maker = MarketMaker(half_spread=0.25, skew_coefficient=0.01, quote_size=20)
    lobster_history = build_lobster_history("data/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_message_10.csv", strategy=lobster_market_maker)
    show_interactive(lobster_history, strategy=lobster_market_maker, title="Real Order Flow Simulation (LOBSTER, AMZN)")

    # LOBSTER timestamps are real seconds-after-midnight (this sample file spans
    # 34200-57600, i.e. 09:30-16:00), so terminal_time=57600 is the actual session
    # close, not an arbitrary tick count. gamma/sigma/k/max_inventory are the best
    # combination found by backtest.py's Avellaneda-Stoikov grid search against
    # this same file (train PnL +21.70, test PnL +2.45) -- rerun that grid search
    # if the data file changes.
    lobster_avellaneda_market_maker = AvellanedaStoikovMarketMaker(gamma=1e-6, sigma=0.01, k=10, terminal_time=57600, quote_size=10, max_inventory=25)
    lobster_avellaneda_history = build_lobster_history("data/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_message_10.csv", strategy=lobster_avellaneda_market_maker)
    show_interactive(lobster_avellaneda_history, strategy=lobster_avellaneda_market_maker, title="Real Order Flow Simulation (LOBSTER, AMZN, Avellaneda-Stoikov)")
