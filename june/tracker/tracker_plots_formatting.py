import numpy as np
from cycler import cycler
import matplotlib as mpl
import matplotlib.font_manager
import matplotlib.pyplot as plt

from june.mpi_setup import mpi_comm, mpi_size, mpi_rank

try:
    plt.style.use(["science", "no-latex", "bright"])
    if mpi_rank == 0:
        print("Using 'science' matplotlib style")
except Exception:
    plt.style.use("default")
    if mpi_rank == 0:
        print("Using default matplotlib style")

dpi = 150

# Some figure initialization
def fig_initialize(setsize=False):
    # Set up tex rendering
    plt.rc("text", usetex=True)
    plt.rc(
        "text.latex",
        preamble=[
            r"\usepackage{amsmath}",
            r"\usepackage{amsthm}",
            r"\usepackage{amssymb}",
            r"\usepackage{amsfonts}",
        ],
    )
    # mpl.rcParams["font.family"] = "serif"
    # mpl.rcParams["font.serif"] = "STIX"
    # mpl.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["savefig.facecolor"] = "white"
    if setsize:
        mpl.rcParams["font.size"] = 10
        mpl.rcParams["lines.linewidth"] = 1
        mpl.rcParams["axes.labelsize"] = 9
        mpl.rcParams["axes.titlesize"] = 8
        mpl.rcParams["xtick.labelsize"] = 8
        mpl.rcParams["ytick.labelsize"] = 8
        mpl.rcParams["legend.labelspacing"] = 0.5
        plt.rc("legend", **{"fontsize": 8})
        plt.rc("legend", **{"frameon": False})
    # plt.tight_layout()

    # Define a custom cycler
    # custom_cycler = (cycler(color=['steelblue','maroon','midnightblue','r','cadetblue','orange']) + \
    #                 cycler(linestyle=['-','-.','--',':','--','-']))

    # plt.rc('axes',prop_cycle=custom_cycler)
    plt.rc("axes")
    return 1


def set_size(width="paper", fraction=1, subplots=(1, 1)):
    """Set figure dimensions to avoid scaling in LaTeX.

    Credit : https://jwalton.info/Embed-Publication-Matplotlib-Latex/

    Parameters
    ----------
    width: float or string
            Document width in points, or string of predined document type
    fraction: float, optional
            Fraction of the width which you wish the figure to occupy
    subplots: array-like, optional
            The number of rows and columns of subplots.
    Returns
    -------
    fig_dim: tuple
            Dimensions of figure in inches
    """
    if width == "paper":
        width_pt = 392.0
    else:
        width_pt = width

    # Width of figure (in pts)
    fig_width_pt = width_pt * fraction
    # Convert from pt to inches
    inches_per_pt = 1 / 72.27

    # Golden ratio to set aesthetic figure height
    golden_ratio = (5**0.5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt
    # Figure height in inches
    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1])

    return (fig_width_in, fig_height_in)


def legend(fig, axes, x0=1, y0=0.5, direction="v", padpoints=3, **kwargs):

    otrans = axes[0].figure.transFigure
    t = axes[0].legend(
        bbox_to_anchor=(x0, y0), loc="center", bbox_transform=otrans, **kwargs
    )

    plt.tight_layout(pad=0)

    axes[0].figure.canvas.draw()
    plt.tight_layout(pad=0)
    ppar = [0, -padpoints / 72.0] if direction == "v" else [-padpoints / 72.0, 0]
    trans2 = (
        mpl.transforms.ScaledTranslation(ppar[0], ppar[1], fig.dpi_scale_trans)
        + axes[0].figure.transFigure.inverted()
    )
    tbox = t.get_window_extent().transformed(trans2)

    if direction == "v":
        for ax in axes:
            bbox = ax.get_position()
            ax.set_position([bbox.x0, bbox.y0, bbox.width, tbox.y0 - bbox.y0])
    else:
        for ax in axes:
            bbox = ax.get_position()
            ax.set_position([bbox.x0, bbox.y0, tbox.x0 - bbox.x0, bbox.height])
