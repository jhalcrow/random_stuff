

# ------------------------------------------------- the decisive Ambusher test CLEARS Ambusher
# Narses fielded 61,785 infantry + 61,785 archers and NO CAVALRY.  I attacked with 1,000 at
# 50/20/30 and won, losing 397 while wiping all 123,570.  With only two enemy types the redirect
# is unambiguous: my cavalry would otherwise pile into his infantry, and Ambusher sends it to the
# archers.
#     Ambusher ON  (tooltip 20%)   my losses 648   k = 1.63
#     Ambusher OFF                 my losses 836   k = 2.11
# Ambusher ON is the CLOSER of the two.  That REVERSES the earlier ablation, where turning it off
# improved the Terry and Narses-mixed cells, and it means Ambusher is not the culprit.  I was
# about to blame a mechanic the game plainly has, on the strength of an ablation that had a
# confound in it.
#
# THE ACTUAL PATTERN, across all eight fights where my own losses are the uncensored quantity:
#
#   fight                          lost     sent   fraction     k
#   Narses pure-archer, 5,000        72    5,000      1.4%   1.04
#   Narses mixed, attack 10,000     239   10,000      2.4%   1.20
#   Narses mixed, defend 5,000      292    5,000      5.8%   1.26
#   Narses inf+arch, 1,000          397    1,000     39.7%   1.63
#   Terry 10k all archer         10,000   10,000    100.0%   1.47
#   Terry 10k all infantry       10,000   10,000    100.0%   1.84
#   opponent-2 10k mixed         10,000   10,000    100.0%   1.66
#   Terry 20k mixed              20,000   20,000    100.0%   2.04
#
#   r = 0.831, across three opponents, four compositions, march sizes 1,000 to 20,000, and both
#   attack and defence.  The more attrition I actually take, the more the model over-predicts it.
#
# That is the signature of a missing damage-ABSORPTION mechanic, and the reference engine has
# exactly one that sim.py has never implemented: Skill.protect(), effects 801 and 901, which soak
# a share of the incoming dead from a pool that refills each round.  It was flagged much earlier
# in this session as "the right shape for a uniform over-kill" -- and then Ambusher got chased
# instead, on the strength of a correlation that turned out to be confounded with attrition.
#
# NEXT: implement Skill.protect().  Its shape predicts exactly this curve -- a fixed absorption
# per round matters little when you lose 1.4% of your army and enormously when you lose all of it.
