from pathlib import Path
import re
p=Path("/out/.config")
s=p.read_text()
for option in ['HALT', 'FEATURE_SH_IS_ASH', 'ASH_BUILTIN_TEST', 'ASH_BUILTIN_ECHO', 'ASH_BUILTIN_PRINTF', 'SH_MATH_SUPPORT', 'FEATURE_FANCY_PING', 'LFS', 'STATIC', 'ASH', 'FEATURE_SH_STANDALONE', 'FEATURE_SH_NOFORK', 'MOUNT', 'UMOUNT', 'FEATURE_MOUNT_FLAGS', 'FEATURE_MOUNT_FSTAB', 'MKDIR', 'MKNOD', 'CAT', 'ECHO', 'PRINTF', 'SLEEP', 'GREP', 'CUT', 'AWK', 'SED', 'CP', 'MV', 'RM', 'LN', 'CHMOD', 'CHOWN', 'SYNC', 'TEST', 'TRUE', 'FALSE', 'IP', 'FEATURE_IP_ADDRESS', 'FEATURE_IP_LINK', 'FEATURE_IP_ROUTE', 'IFCONFIG', 'ROUTE', 'UDHCPC', 'HOSTNAME', 'KILL', 'KILLALL', 'PS', 'FREE', 'DMESG', 'UNAME', 'READLINK', 'ENV', 'LS', 'TOUCH', 'MDEV', 'INSMOD', 'LSMOD', 'RMMOD', 'MODPROBE', 'FEATURE_MODUTILS_ALIAS', 'NC', 'FEATURE_IPV6', 'PING', 'PING6', 'FIND', 'WC', 'HEAD', 'TAIL', 'TR', 'SORT', 'STTY']:
    s=re.sub(r"(?m)^(?:# CONFIG_"+option+r" is not set|CONFIG_"+option+r"=.*)$", "CONFIG_"+option+"=y",s)
s=s.replace("CONFIG_FEATURE_SH_IS_NONE=y", "# CONFIG_FEATURE_SH_IS_NONE is not set")
p.write_text(s)
