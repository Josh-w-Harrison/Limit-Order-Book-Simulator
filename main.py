import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

from market_data import MarketDataGenerator, HistoricalMarketDataGenerator, LOBSTERMarketDataGenerator
from order_book import OrderBook
from simulator import Simulator


def build_synthetic_history(n_ticks, initial_price=100.0, seed=None):
    """
    Build a synthetic simulation run (random-walk reference price) and
    return the history list of dicts, ready to be passed to
    show_interactive().
    """
    market_data_generator = MarketDataGenerator(initial_price=initial_price, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed)
    history = simulator.run(n_ticks)
    return history


def build_historical_history(csv_path, n_ticks, seed=None):
    """
    Build a simulation run driven by a real historical price series (see
    fetch_historical_data.py / HistoricalMarketDataGenerator) and return
    the history list of dicts, ready to be passed to show_interactive().
    """
    market_data_generator = HistoricalMarketDataGenerator(csv_path, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed)
    history = simulator.run(n_ticks)
    return history


def build_lobster_history(message_csv_path, seed=None):
    """
    Build a simulation run replaying real order-by-order flow from a
    LOBSTER message file and return the history list of dicts, ready to
    be passed to show_interactive(). Uses run_replay() instead of
    run(n_ticks), since the message file itself determines how many
    events exist rather than a fixed tick count.
    """
    market_data_generator = LOBSTERMarketDataGenerator(message_csv_path, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed)
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


def show_interactive(history, title="Simulation"):
    """
    Build the matplotlib figure: top panel with the four price series
    and a slider, bottom panel with the depth chart for whichever step
    the slider is on. Blocks on plt.show().
    """
    # Real replays (e.g. LOBSTER) carry a real timestamp per entry; synthetic/
    # historical runs don't, so fall back to the step index as the x-axis.
    x = [entry.get('timestamp') if entry.get('timestamp') is not None else i
         for i, entry in enumerate(history)]
    x_label = 'Time (seconds after midnight)' if history[0].get('timestamp') is not None else 'Step'
    reference_prices = [entry['reference_price'] if entry['reference_price'] is not None else float('nan') for entry in history]
    mid_prices = [entry['mid_price'] if entry['mid_price'] is not None else float('nan') for entry in history]
    best_bids = [entry['best_bid'] if entry['best_bid'] is not None else float('nan') for entry in history]
    best_asks = [entry['best_ask'] if entry['best_ask'] is not None else float('nan') for entry in history]

    fig, (ax_price, ax_depth) = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title(title)
    plt.subplots_adjust(bottom=0.2, hspace=0.4)

    ax_price.plot(x, reference_prices, label='Reference Price', color='blue')
    ax_price.plot(x, mid_prices, label='Mid Price', color='green')
    ax_price.plot(x, best_bids, label='Best Bid', color='orange')
    ax_price.plot(x, best_asks, label='Best Ask', color='red')
    ax_price.set_xlabel(x_label)
    ax_price.set_ylabel('Price')
    ax_price.set_title('Price Evolution Over Time')
    ax_price.legend()

    current_marker = ax_price.axvline(x=x[0], color='black', linestyle='--')

    _draw_depth(ax_depth, history[0]['depth_snapshot'])

    slider_ax = fig.add_axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(slider_ax, 'Step', valmin=0, valmax=len(history) - 1, valinit=0, valstep=1)

    def on_slider_change(val):
        step = int(slider.val)
        current_marker.set_xdata([x[step], x[step]])
        _draw_depth(ax_depth, history[step]['depth_snapshot'])
        fig.canvas.draw_idle()

    slider.on_changed(on_slider_change)

    plt.show()


if __name__ == "__main__":
    synthetic_history = build_synthetic_history(n_ticks=400, seed=42)
    show_interactive(synthetic_history, title="Synthetic Data Simulation")

    historical_history = build_historical_history("data/AAPL_1m.csv", n_ticks=400, seed=42)
    show_interactive(historical_history, title="Historical Data Simulation (AAPL, 1m)")

    lobster_history = build_lobster_history(
        "data/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_message_10.csv"
    )
    show_interactive(lobster_history, title="Real Order Flow Simulation (LOBSTER, AMZN)")
