include $(TOPDIR)/rules.mk

PKG_NAME:=wemo-matter-outlet
PKG_VERSION:=0.1
PKG_RELEASE:=1
PKG_LICENSE:=Apache-2.0
PKG_MAINTAINER:=wemo_matter development

include $(INCLUDE_DIR)/package.mk

define Package/wemo-matter-outlet
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Development Matter outlet with simulated relay
  DEPENDS:=@TARGET_ramips
endef

define Package/wemo-matter-outlet/description
  Cross-built development payload. Physical relay, production credentials and
  board compatibility remain unvalidated. Service is disabled by default.
endef

define Package/wemo-matter-outlet/conffiles
/etc/config/wemo-matter
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
endef

# Explicitly supplied, tested static firmware-profile executable; no download.
define Build/Compile
	[ -n "$(WEMO_MATTER_BIN)" ] && [ -n "$(WEMO_MATTER_SHA256)" ]
	echo "$(WEMO_MATTER_SHA256)  $(WEMO_MATTER_BIN)" | sha256sum -c -
	$(CP) $(WEMO_MATTER_BIN) $(PKG_BUILD_DIR)/wemo-matter-outlet
endef

define Package/wemo-matter-outlet/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/etc/init.d $(1)/etc/config $(1)/etc/wemo-matter/state
	chmod 700 $(1)/etc/wemo-matter/state
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/wemo-matter-outlet $(1)/usr/bin/
	$(INSTALL_BIN) ./files/wemo-matter.init $(1)/etc/init.d/wemo-matter
	$(INSTALL_CONF) ./files/wemo-matter.config $(1)/etc/config/wemo-matter
endef

$(eval $(call BuildPackage,wemo-matter-outlet))
