FROM alpine:latest

RUN apk --no-cache add openssh \
    && sed -i -e "s/#PermitRootLogin prohibit-password/PermitRootLogin yes/" /etc/ssh/sshd_config \
    && ssh-keygen -A

RUN adduser -D -s /bin/bash sshuser \
    && echo "sshuser:password" | chpasswd

RUN mkdir -p /home/sshuser/.ssh \
    && chmod 700 /home/sshuser/.ssh

# We will mount the public key from the hotplots container
# so we don't need to copy it here.

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
