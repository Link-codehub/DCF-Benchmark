#!/bin/sh
set -eu
ready=/tmp/dcf-egress-ready
rm -f "$ready"
# Use IPv4 fib rather than the unavailable inet-family fib module.
nft -f - <<'EOF'
add table ip dcf_egress
flush table ip dcf_egress
table ip dcf_egress {
  chain output {
    type filter hook output priority filter; policy drop;
    oif "lo" accept
    fib daddr type local accept
    ip daddr 192.168.65.254 tcp dport 4311 accept
    ct state established,related accept
  }
}
EOF
sleep 1
touch "$ready"
echo "IPv4 egress policy: only host-gateway model relay port 4311"
sleep infinity
