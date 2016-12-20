# boottime
Usage:
1/ boot up android to UI
2/ run script # python parse_coldboot_progress.py
3/ result print on console and logs/#current_time#/out.result

Result format:

... show boot_progress result ...
1    2  stage                                        time point (second)
---------------------
init_start          ,                       5.35
    initializing_selinux,                   5.425
    .coldboot_done      ,                   5.758
    load_default_prop   ,                   5.508
    load_system_prop    ,                   6.696
    load_vendor_prop    ,                   6.706
    load_factory_prop   ,                   6.706
    load_data_local_prop,                   11.233
    cache_mount         ,                   6.064
    config_mount        ,                   6.472
    data_mount          ,                   10.927
zygote_start        ,                           12.443
preload_start       ,                           13.008
preload_end         ,                           14.003
system_run          ,                           14.069
pms_system_scan_start,                          14.444
pms_data_scan_start ,                           16.825
pms_scan_end        ,                           16.83
pms_ready           ,                           16.902
ams_ready           ,                           19.309
enable_screen       ,                           22.004
bootanim_exit       ,                           22.339

... show service_start result …
Name                         ,                       time point,          on-trigger
-------------------
ueventd                       ,                 5.602,          early-init
logd                          ,                 6.655,          property:vold.decrypt=trigger_load_persist_props
vold                          ,                  6.73,          post-fs-data
exec 0 (/system/bin/tzdatacheck),                       6.746,
logd-reinit                   ,                 6.879,          property:vold.decrypt=trigger_load_persist_props
healthd                       ,                 6.978,
lmkd                          ,                 6.983,
servicemanager                ,                 6.993,
surfaceflinger                ,                 6.999,          property:vold.decrypt=trigger_encryption
reset_usb                     ,                 7.005,
watchdogd                     ,                  7.01,             charger
intel_prop                    ,                 7.015,
earlylogs                     ,                 7.027,
dvc_desc                      ,                 7.032,
bootanim                      ,                  9.15,
rfkill-init                   ,                 9.305,                boot
ioc_slcand                    ,                 10.014,               boot
console                       ,                 10.033,         property:ro.debuggable=1
gfxd                          ,                 10.054,         property:persist.gen_gfxd.enable=1
defaultcrypto                 ,                 10.076,         property:vold.decrypt=trigger_default_encryption
adbd                          ,                 10.755,         property:sys.usb.config=accessory,audio_source,adb
logd-reinit                   ,                 11.289,         property:vold.decrypt=trigger_load_persist_props
ap_log_srv                    ,                 11.31,
apk_logfs                     ,                 11.362,
exec 1 (/system/bin/tzdatacheck),                       11.39,
netd                          ,                 11.522,
debuggerd                     ,                 11.527,
debuggerd64                   ,                 11.532,
drm                           ,                 11.544,
media                         ,                 11.549,
installd                      ,                 11.554,
flash_recovery                ,                 11.559,
keystore                      ,                 11.565,
msync                         ,                 11.57,
coreu                         ,                 11.575,
esif_ufd                      ,                 11.58,
hdcpd                         ,                 11.585,
ufipc_daemon_app              ,                 11.59,
gptp                          ,                 11.597,
zygote                        ,                 11.601,
zygote_secondary              ,                 11.607,
gatekeeperd                   ,                 11.613,
perfprofd                     ,                 11.625,
dirana_config                 ,                 11.631,
pstore-clean                  ,                 11.639,
init_npk                      ,                 11.645,         property:npk.cfg.update=*
crashlogd                     ,                 11.65,
log-watch                     ,                 11.655,
power_hal_helper              ,                 11.678,         property:init.svc.media=running
p2p_supplicant                ,                 19.492,


