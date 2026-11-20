# Craft registry (instance state in the craft zone, Rule-11 property 2; #156)

One row per *installed* craft, never written by hand: a Tended craft's by `dyad craft install`, the core
craft's (`dyad-operator`, tree `dyad/`) by `dyad install` (#199). A craft authored in this system has no row
(`dyad craft list` shows it as `authored`). `sha256` is `distribute.archive_sha256` of the installed tree —
the proof it is unmodified, and what lets the push gate skip its test root (Rule-12 property 2); `source` is
where the archive came from (a `world` reference); `d-work` the installing d-work. No date: a second install
of the same version changes nothing.

| craft | version | source | sha256 | d-work |
|-------|---------|--------|--------|--------|
| cabinet | 0.9.0 | dyad-1.6.0.tar.gz | 060426ccc21f6bd3372c91806c3a4c1c0ddba41c6737f3a83dbfff462783888a |  |
| channels | 0.2.0 | dyad-1.6.0.tar.gz | ef49726b1fe037c8042ae7e229a0aa33240f41cff9ee34cd8c25b0125a824069 |  |
| dyad-operator | 1.6.0 | dyad-1.6.0.tar.gz | e711ade9866fb3567cbccaff58e4bed8bef12752df41d9e88931eb58db5bd417 |  |
| sysadmin | 0.3.3 | dyad-1.6.0.tar.gz | 6ce4b36891b31fb6b6fba93c896989edff37176517e531422a566318d0044200 |  |
| sysarch | 0.4.2 | dyad-1.6.0.tar.gz | 4aa632be524829d2486d80719e8d9b7574238da231b45b014e9020f69e0d5e5c |  |
| syseng | 0.8.1 | dyad-1.6.0.tar.gz | 3a0206c724ac604808545725a8b28d0f650241292a5e3fbdb0e970122be07830 |  |
