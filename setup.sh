# Source this file to set up the environment for TrkCondTuning:
#   source /path/to/TrkCondTuning/setup.sh
# Work area: $TCT_MUSEWORK if set, else the parent directory of this repository if it is a
# muse work area (has a build/ directory or .muse).
_tct_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_tct_work="${TCT_MUSEWORK:-}"
if [ -z "$_tct_work" ]; then
  _tct_parent="$(dirname "$_tct_repo")"
  if [ -d "$_tct_parent/build" ] || [ -e "$_tct_parent/.muse" ]; then
    _tct_work="$_tct_parent"
  fi
fi
if [ -z "$_tct_work" ] || [ ! -d "$_tct_work" ]; then
  echo "TrkCondTuning setup: no muse work area found. Set TCT_MUSEWORK to a muse work area" \
       "(a directory with a build/ directory), or clone this repository into one." >&2
  unset _tct_repo _tct_work _tct_parent
  return 1 2>/dev/null || exit 1
fi
export TCT_MUSEWORK="$_tct_work"
export TCT_REPO="$_tct_repo"
source /cvmfs/mu2e.opensciencegrid.org/setupmu2e-art.sh
# The driver (and the metrics) run in the Mu2e python analysis environment (uproot, awkward,
# matplotlib). The mu2e jobs get the muse environment of $TCT_MUSEWORK, captured in a subshell
# by trkcondtuning/env.py, so muse is NOT set up in this shell (the two environments conflict).
pyenv rootana ${TCT_ROOTANA_VERSION:-2.5.0}
export PYTHONPATH="$_tct_repo${PYTHONPATH:+:$PYTHONPATH}"
export PATH="$_tct_repo/bin:$PATH"
unset _tct_repo _tct_work _tct_parent
