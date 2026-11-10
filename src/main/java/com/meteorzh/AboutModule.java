/*
 * Meteor-ZH - Meteor Client 简体中文汉化
 * Copyright (C) 2026 woo4005
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

package com.meteorzh;

import meteordevelopment.meteorclient.settings.BoolSetting;
import meteordevelopment.meteorclient.settings.Setting;
import meteordevelopment.meteorclient.settings.SettingGroup;
import meteordevelopment.meteorclient.systems.modules.Category;
import meteordevelopment.meteorclient.systems.modules.Module;
import meteordevelopment.meteorclient.utils.player.ChatUtils;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.network.chat.Component;

/**
 * 「关于汉化插件」—— 这个模块本身就是汉化插件自己的控制面板。
 *
 * <p>所有字符串在源码里直接写成中文，不经过词典、不需要翻译；即使用户把词典整个删掉，
 * 这个面板照样是中文（这也是它能当「排障入口」的原因）。
 *
 * <h2>为什么用一串开关做按钮</h2>
 *
 * <p>Meteor 的模块设置面板只认识「设置项」，没有「按钮」这种控件。想做到「点一下就
 * 触发一次动作」，标准做法就是给一个 {@link BoolSetting}，在 {@code onChanged} 里执行
 * 动作后立刻把它改回 {@code false} —— 界面上看就是一个点了会自己弹回去的开关。
 * 三个一次性开关（显示信息 / 立即检查 / 打开下载页）都是这么实现的。
 *
 * <h2>为什么开启模块本身会打印信息</h2>
 *
 * <p>模块名「关于汉化插件」暗示它是「关于」页面，所以 {@link #onActivate()} 直接把
 * 版本、词典规模、更新状态打到聊天栏（主菜单里则用右下角弹窗），省得玩家去翻设置。
 */
public class AboutModule extends Module {
    private static AboutModule instance;

    /** 一次性开关：显示插件信息。 */
    public final Setting<Boolean> showInfo;
    /** 一次性开关：立即检查更新。 */
    public final Setting<Boolean> checkNow;
    /** 一次性开关：打开 GitHub 下载页面。 */
    public final Setting<Boolean> openPage;
    /** 每次启动自动检查一次更新（默认开）。 */
    public final Setting<Boolean> autoCheck;
    /** 自动检查命中新版本时后台静默下载，退出游戏后替换（默认关）。 */
    public final Setting<Boolean> autoDownload;

    public AboutModule(Category category) {
        super(category, "关于汉化插件", "查看汉化插件的版本、词典规模与更新状态；也可以在这里检查更新或打开下载页面。");

        // 主菜单里也要能打开：玩家往往在进游戏前就想看看有没有新版本。
        runInMainMenu = true;
        // 本模块不监听任何事件，关掉自动订阅省一点开销。
        autoSubscribe = false;

        instance = this;

        showInfo = new BoolSetting.Builder()
            .name("显示插件信息")
            .description("打开后把插件版本、词典条数与当前更新状态打印到聊天栏。")
            .defaultValue(false)
            .onChanged(value -> oneShot(value, this::printInfo))
            .build();

        checkNow = new BoolSetting.Builder()
            .name("立即检查更新")
            .description("马上访问一次 GitHub 检查新版本（不受「每次启动只检查一次」限制）。")
            .defaultValue(false)
            .onChanged(value -> oneShot(value, UpdateChecker::checkManual))
            .build();

        openPage = new BoolSetting.Builder()
            .name("打开下载页面")
            .description("用系统浏览器打开 GitHub 的 Releases 页面。")
            .defaultValue(false)
            .onChanged(value -> oneShot(value, UpdateChecker::openDownloadPage))
            .build();

        autoCheck = new BoolSetting.Builder()
            .name("自动检测更新")
            .description("每次启动游戏时访问一次 GitHub，有新版就在聊天栏或右下角提示。检查失败会安静放弃。")
            .defaultValue(true)
            .build();

        autoDownload = new BoolSetting.Builder()
            .name("自动下载更新")
            .description("自动检测到新版本时后台静默下载；关闭游戏后自动替换旧插件，下次启动即为新版本。")
            .defaultValue(false)
            .visible(autoCheck::get)
            .build();

        SettingGroup general = settings.getDefaultGroup();
        general.add(showInfo);
        general.add(checkNow);
        general.add(openPage);

        SettingGroup update = settings.createGroup("更新");
        update.add(autoCheck);
        update.add(autoDownload);
    }

    /** 供其它类拿实例（启动检查要读 autoCheck / autoDownload）。 */
    public static AboutModule get() {
        return instance;
    }

    @Override
    public String getInfoString() {
        return "v" + UpdateChecker.currentVersion();
    }

    @Override
    public void onActivate() {
        printInfo();
    }

    /**
     * 一次性开关的通用处理：把开关拨回 false 再执行动作，界面上就像按了个按钮。
     *
     * <p>配置加载阶段 {@link MeteorZh#started()} 还是 false，此时若发现值为 true（上次
     * 异常退出留下的），只负责拨回去，不触发任何网络或 IO。
     */
    private void oneShot(boolean value, Runnable action) {
        if (!value) return;

        if (!MeteorZh.started()) {
            resetOneShotFlags();
            return;
        }

        // 先拨回去；这会再次触发 onChanged(false)，上面的 !value 分支直接返回，不会递归。
        resetOneShotFlags();

        try {
            action.run();
        } catch (Throwable t) {
            MeteorZh.LOG.warn("Meteor-zh: about-action failed", t);
            announce("操作失败：" + t.getClass().getSimpleName());
        }
    }

    private void resetOneShotFlags() {
        if (showInfo.get()) showInfo.set(false);
        if (checkNow.get()) checkNow.set(false);
        if (openPage.get()) openPage.set(false);
    }

    /** 打印一行行信息：在世界里走聊天栏，在主菜单走右下角弹窗。 */
    public void printInfo() {
        String[] lines = {
            "Meteor 中文汉化 v" + UpdateChecker.currentVersion() + "（Minecraft " + UpdateChecker.mcVersion() + "）",
            "词典：" + ZhDict.summaryText() + "；词表：" + WordTranslator.size() + " 个词元",
            "渲染：" + FontFixer.describe(),
            "更新：" + UpdateChecker.statusText(),
            UpdateChecker.summaryLine(),
            "下载页：" + UpdateChecker.RELEASES_PAGE
        };

        if (inWorld()) {
            // ChatUtils.info 内部会做 String.format，文案里一旦出现 % 就会抛异常 —— 统一走 %s。
            for (String line : lines) ChatUtils.info("%s", line);
        } else {
            toast("Meteor 中文汉化", lines[0] + " · " + UpdateChecker.statusText());
        }
    }

    /** 供别的一次性动作使用的提示通道。 */
    static void announce(String message) {
        UpdateChecker.notifyLater(message, "Meteor 汉化");
    }

    private static boolean inWorld() {
        Minecraft mc = Minecraft.getInstance();
        return mc != null && mc.level != null && mc.player != null;
    }

    private static void toast(String title, String subtitle) {
        try {
            Minecraft mc = Minecraft.getInstance();
            if (mc == null) return;
            SystemToast.add(mc.getToastManager(), new SystemToast.SystemToastId(6000L),
                Component.literal(title), Component.literal(subtitle));
        } catch (Throwable t) {
            MeteorZh.LOG.warn("Meteor-zh: failed to show toast", t);
        }
    }
}
