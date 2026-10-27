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
import meteordevelopment.meteorclient.events.world.TickEvent;
import meteordevelopment.meteorclient.commands.Commands;
import meteordevelopment.orbit.EventHandler;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Meteor-zh: Chinese translation for Meteor Client and every installed addon.
 *
 * Translation strategy
 *  1. English display strings of already built objects are rewritten in place
 *     through reflection (see {@link Translator}). That covers module names,
 *     descriptions, every setting label and tooltip, category tabs and HUD
 *     element names, and it survives a restart because it is re-applied on each
 *     launch.
 *  2. Hard-coded GUI phrases that a field rewrite cannot reach ("Bind: ",
 *     "Toggle on bind release: ", setting group headings, ...) are replaced in
 *     the render path by {@link com.meteorzh.mixin.GuiRendererMixin}.
 *
 * Nothing is persisted, so there is no stale state to invalidate: restart the
 * game and the translation is applied again automatically.
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
        if (done) return;
        done = true;

        try {
            ZhDict.load();
            Translator.init();
            Translator.translateAll();
            Commands.add(new ZhCommand());
            LOG.info("Meteor-zh: ready (.zh reload to re-apply)");
        } catch (Throwable t) {
            LOG.error("Meteor-zh: initialisation failed", t);
        } finally {
            meteordevelopment.meteorclient.MeteorClient.EVENT_BUS.unsubscribe(this);
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
