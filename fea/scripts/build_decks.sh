#!/bin/bash
# Build the 12 Nastran input decks of the idealised reference model (0-60 kPa) in model/<run>/.
# Usage (Git Bash or any bash):  bash scripts/build_decks.sh [--mesh]
#   --mesh  also rebuild model/mesh_M0.pkl from cad/geometry/ (otherwise the committed mesh is used)
set -e
cd "$(dirname "$0")"
M=../model
PY=${PY:-python}
if [ "$1" = "--mesh" ]; then
  $PY -P make_mesh.py --level M0 --out $M --norender
fi
FIX="--rigid_leg --bond_skin --padE 9.65 --core 25 --slstab 1e-4 --cov_endiso 0.7 --floor_bond --tissue contracted --calib $M/calib_rigid.json --mesh $M/mesh_M0.pkl"
deck() {   # deck <run> <make_deck options...>
  n=$1; shift; mkdir -p $M/$n
  $PY -P make_deck.py $FIX --out $M/$n/$n.nas --run $n "$@" > $M/$n/gen.log 2>&1
  $PY -P seal_check.py $M/$n/$n.nas $M/$n/${n}_mesh.pkl > /dev/null 2>&1 || true   # writes <run>_seal_check.txt
  tail -1 $M/$n/gen.log
}
# fixed-angle cases: bend vented to the angle, then pressurise. CHK_FB is the 3 deg case; its deck also lists 80 and
# 100 kPa, which were not reached (the run stopped near 70 kPa) and are not used.
deck CHK_FB   --seq MULTI --theta 3.0  --plist 20,40,60,80,100
for a in 7.3:7.28 8.6:8.63 9.8:9.78 13.0:13.0 16.0:16.0 19.0:19.0; do
  deck HC_A${a%%:*} --seq MULTI --theta ${a##*:} --plist 20,40,60
done
# gait cycles (assist window 13-36 % stance)
deck HCC_P0   --seq CYCLE --cyc_p 0
deck HCC_P20  --seq CYCLE --cyc_p 20
deck HCC_PROJ --seq CYCLE --cyc_p PROJ --cyc_end 36
deck HCC_P40  --seq CYCLE --cyc_p 40 --cyc_end 36 --cyc_step 3
deck HCC_P60  --seq CYCLE --cyc_p 60 --cyc_end 36 --cyc_step 3
