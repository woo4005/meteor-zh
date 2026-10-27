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

package com.meteorzh.mixin;

import com.meteorzh.ZhDict;
import meteordevelopment.meteorclient.gui.renderer.GuiRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Render-layer translation for hard-coded GUI phrases.
 *
 * Every text drawn in Meteor's GUI funnels through
 * {@code GuiRenderer.text(String text, double x, double y, Color color, boolean title)}.
 * Rewriting its first argument here catches the strings that are baked into the
 * screen code and therefore cannot be reached by a field rewrite:
 * setting group headings ("General", "Render", ...), the module screen labels
 * ("Bind: ", "Toggle on bind release: ", "Chat Feedback: ", "Active: "),
 * section titles, button captions and tooltips.
 *
 * The method signature contains no Minecraft types, so no remapping or refmap
 * entry is needed — it is identical in mojmap and intermediary.
 */
@Mixin(value = GuiRenderer.class, remap = false)
public class GuiRendererMixin {
    @ModifyVariable(method = "text", at = @At("HEAD"), argsOnly = true, remap = false)
    private String meteorzh$translate(String text) {
        return ZhDict.ui(text);
    }
}
