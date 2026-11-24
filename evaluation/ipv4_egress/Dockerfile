FROM alpine:3.23.4
RUN apk add --no-cache nftables bash
COPY firewall.sh /firewall.sh
COPY --chmod=755 network-policy /usr/local/bin/network-policy
ENTRYPOINT ["/bin/sh", "/firewall.sh"]
