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
import meteordevelopment.orbit.EventHandler;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
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

    private boolean done;

    @Override
    public void onInitialize() {
        LOG.info("Meteor-zh: starting (Meteor addon)");

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
            Translator.init();
            Translator.translateAll();
            Commands.add(new ZhCommand());
            LOG.info("Meteor-zh: ready (.zh reload to re-apply, .zh info for stats)");
        } catch (Throwable t) {
            LOG.error("Meteor-zh: initialisation failed", t);
        }
    }

    @Override
    public void onRegisterCategories() {
        // no categories of our own
    }

    @Override
    public String getPackage() {
        return "com.meteorzh";
    }
}
