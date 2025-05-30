import time
import matplotlib.pyplot as plt
import numpy as np

class timetrack():
    def __init__(self, timer=time.perf_counter):
        self.timer = timer
        self.times = {}
        self.starts = {}

    def start(self, prop):
        self.starts[prop] = self.timer()

    def stop(self, prop):
        stop = self.timer()
        if prop not in self.times:
            self.times[prop] = [ stop - self.starts[prop] ]
        self.times[prop].append( stop - self.starts[prop])

    def boxplot(self, show=True):
        labels = list(self.times.keys())
        data = list(self.times.values())

        # Ignore empty entries
        empty = [i for i, d in enumerate(data) if len(d) == 0]
        for i in reversed(empty):
            data.pop(i)
            labels.pop(i)

        n = len(labels)
        fig, ax = plt.subplots(figsize=(max(6, n*1.2), 5))

        # Create boxplot with mean markers
        bp = ax.boxplot(
            data,
            labels=labels,
            vert=True,
            patch_artist=True,
            showmeans=True,
            meanprops={'marker':'D', 'mfc':'white', 'mec':'black'}
        )

        # Add ±1σ horizontal lines
        for i, (label, values) in enumerate(self.times.items(), 1):
            mean = np.mean(values)
            std = np.std(values)

            # Add horizontal lines for mean ±1σ
            ax.hlines(
                [mean - std, mean + std],
                xmin=i-0.4, xmax=i+0.4,  # Match default box width
                colors='red',
                linestyles='dashed',
                linewidth=1
            )

        ax.set_title("Execution times")
        ax.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()

        if show:
            fig.show()

        return fig

tracker = timetrack()
