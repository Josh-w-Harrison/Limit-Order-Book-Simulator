import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

from market_data import MarketDataGenerator
from order_book import OrderBook
from simulator import Simulator


def build_history(n_ticks, initial_price=100.0, seed=None):
    """
    Build a synthetic simulation run and return the history list of dicts
    for each step, ready to be passed to show_interactive().
    """
    market_data_generator = MarketDataGenerator(initial_price=initial_price, seed=seed)
    order_book = OrderBook()
    simulator = Simulator(order_book, market_data_generator, seed=seed)
    history = simulator.run(n_ticks)
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


def show_interactive(history):
    """
    Build the matplotlib figure: top panel with the four price series
    and a slider, bottom panel with the depth chart for whichever step
    the slider is on. Blocks on plt.show().
    """
    x = list(range(len(history)))
    reference_prices = [entry['reference_price'] for entry in history]
    mid_prices = [entry['mid_price'] if entry['mid_price'] is not None else float('nan') for entry in history]
    best_bids = [entry['best_bid'] if entry['best_bid'] is not None else float('nan') for entry in history]
    best_asks = [entry['best_ask'] if entry['best_ask'] is not None else float('nan') for entry in history]

    fig, (ax_price, ax_depth) = plt.subplots(2, 1, figsize=(10, 8))
    plt.subplots_adjust(bottom=0.2, hspace=0.4)

    ax_price.plot(x, reference_prices, label='Reference Price', color='blue')
    ax_price.plot(x, mid_prices, label='Mid Price', color='green')
    ax_price.plot(x, best_bids, label='Best Bid', color='orange')
    ax_price.plot(x, best_asks, label='Best Ask', color='red')
    ax_price.set_xlabel('Step')
    ax_price.set_ylabel('Price')
    ax_price.set_title('Price Evolution Over Time')
    ax_price.legend()

    current_marker = ax_price.axvline(x=0, color='black', linestyle='--')

    _draw_depth(ax_depth, history[0]['depth_snapshot'])

    slider_ax = fig.add_axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(slider_ax, 'Step', valmin=0, valmax=len(history) - 1, valinit=0, valstep=1)

    def on_slider_change(val):
        step = int(slider.val)
        current_marker.set_xdata([step, step])
        _draw_depth(ax_depth, history[step]['depth_snapshot'])
        fig.canvas.draw_idle()

    slider.on_changed(on_slider_change)

    plt.show()


if __name__ == "__main__":
    history = build_history(n_ticks=200, seed=42)
    show_interactive(history)
