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

import meteordevelopment.meteorclient.addons.MeteorAddon;
import meteordevelopment.meteorclient.commands.Commands;
import meteordevelopment.meteorclient.events.world.TickEvent;
import meteordevelopment.meteorclient.systems.modules.Category;
import meteordevelopment.meteorclient.systems.modules.Modules;
import meteordevelopment.orbit.EventHandler;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Meteor-zh: Chinese translation for Meteor Client and every installed addon.
 *
 * <h2>How the text is translated</h2>
 *
 * <ol>
 *   <li>English display strings of already-built objects are rewritten in place
 *       through reflection (see {@link Translator}). That covers module names,
 *       descriptions, every setting label and tooltip, category tabs, top-bar tab
 *       names and HUD element titles. Nothing is persisted, so the pass simply
 *       runs again on the next launch and a stale config can never win.</li>
 *   <li>Hard-coded GUI phrases that a field rewrite cannot reach ({@code "Bind: "},
 *       {@code "Toggle on bind release: "}, setting group headings, buttons…) are
 *       replaced in the render path by {@link com.meteorzh.mixin.GuiRendererMixin}.</li>
 *   <li>Identifiers that no dictionary entry covers fall back to word-by-word
 *       synthesis in {@link WordTranslator}, which is what makes an addon the
 *       translator has never seen still readable.</li>
 * </ol>
 *
 * <h2>Why the first tick, and why the font switch</h2>
 *
 * <p>{@code onInitialize()} runs before Meteor registers any module, so the
 * translation pass is deferred to the first client tick — by then every module,
 * setting and HUD element exists and the saved config has been applied.
 *
 * <p>The same tick also flips Meteor over to Minecraft's font renderer, without
 * which translated text is invisible (see {@link FontFixer} for the full story).
 * Both jobs happen once; the event handler unsubscribes immediately afterwards so
 * a normal session pays nothing.
 */
@Environment(EnvType.CLIENT)
public class MeteorZh extends MeteorAddon {
    public static final String MOD_ID = "meteor-zh";
    public static final Logger LOG = LoggerFactory.getLogger(MOD_ID);

    /** 我们自己的模块分类（「汉化」），在 {@link #onRegisterCategories()} 里创建。 */
    private static Category category;
    /** 一次性初始化是否已完成，供「关于汉化插件」的一次性开关判断。 */
    private static volatile boolean started;

    private boolean done;

    @Override
    public void onInitialize() {
        LOG.info("Meteor-zh: starting (Meteor addon)");

        // 控制面板模块。分类在 onRegisterCategories 里已注册，此时可以安全入库。
        try {
            if (category != null) {
                Modules.get().add(new AboutModule(category));
                LOG.info("Meteor-zh: AboutModule registered");
            } else {
                LOG.warn("Meteor-zh: category missing, AboutModule skipped");
            }
        } catch (Throwable t) {
            LOG.error("Meteor-zh: failed to register AboutModule", t);
        }

        // Modules are registered after addons initialise, so the actual pass has to be
        // deferred to the first client tick.
        meteordevelopment.meteorclient.MeteorClient.EVENT_BUS.subscribe(this);
    }

    @EventHandler
    private void onTick(TickEvent.Post event) {
        // One-shot: unsubscribe before doing the work so a failure here cannot
        // produce a log flood on every following tick.
        if (done) return;
        done = true;
        try {
            meteordevelopment.meteorclient.MeteorClient.EVENT_BUS.unsubscribe(this);
        } catch (Throwable ignored) {
            // Not fatal — the guard above already makes this handler a no-op.
        }

        try {
            // Font first: the very next frame should already draw Chinese, and the
            // dictionary load below is the slow part (hundreds of ms on cold start).
            FontFixer.ensureVanillaRenderer();

            ZhDict.load();
            ChatDict.load();
            Translator.init();
            Translator.translateAll();
            Commands.add(new ZhCommand());

            // 到这里一次性初始化完成；之后配置里的「一次性开关」才允许真正触发动作。
            started = true;

            // 每次启动只查一次更新（内部有闸门），网络不通就安静放弃。
            UpdateChecker.checkOnStartup();

            LOG.info("Meteor-zh: ready (.zh reload to re-apply, .zh info for stats)");
        } catch (Throwable t) {
            started = true;
            LOG.error("Meteor-zh: initialisation failed", t);
        }
    }

    /**
     * 一次性初始化是否已经跑完。
     *
     * <p>{@link AboutModule} 的一次性开关（显示信息 / 立即检查 / 打开下载页）靠它来判断
     * 「现在是玩家点的」还是「配置加载时把上次的 true 读回来了」—— 后者必须忽略，
     * 否则每次启动都会莫名其妙访问一次网络或弹出信息。
     */
    public static boolean started() {
        return started;
    }

    @Override
    public void onRegisterCategories() {
        // 自己的分类：翻译插件的控制面板都放在这里（「关于汉化插件」）。
        // 必须在 REGISTERING 期间注册，否则 Modules.registerCategory 会拒绝。
        try {
            category = createCategory("汉化");
            Modules.registerCategory(category);
            LOG.info("Meteor-zh: category registered");
        } catch (Throwable t) {
            LOG.error("Meteor-zh: failed to register category", t);
        }
    }

    /**
     * 创建一个带图标的分类，兼容两条线的 API 差异。
     *
     * <p>1.21.11 的 Meteor 里 {@code Category} 的第二参数是 {@code ItemStack}，
     * 26.1 起改成了 {@code Supplier<ItemStack>}。源码要一份编两个版本，所以这里按
     * 构造器签名反射挑一个能用的；两个都对不上就退化成无图标构造器（图标变成空槽，
     * 但分类仍然可用，不至于因为一个图标让插件起不来）。
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Category createCategory(String name) throws Exception {
        for (java.lang.reflect.Constructor<?> constructor : Category.class.getConstructors()) {
            Class<?>[] params = constructor.getParameterTypes();
            if (params.length != 2 || params[0] != String.class) continue;

            if (params[1] == ItemStack.class) {
                return (Category) constructor.newInstance(name, new ItemStack(Items.WRITABLE_BOOK));
            }
            if (java.util.function.Supplier.class.isAssignableFrom(params[1])) {
                java.util.function.Supplier<ItemStack> icon = () -> new ItemStack(Items.WRITABLE_BOOK);
                return (Category) constructor.newInstance(name, icon);
            }
        }
        return (Category) Category.class.getConstructor(String.class).newInstance(name);
    }

    @Override
    public String getPackage() {
        return "com.meteorzh";
    }
}
