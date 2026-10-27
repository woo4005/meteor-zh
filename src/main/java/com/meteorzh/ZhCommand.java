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

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import meteordevelopment.meteorclient.commands.Command;
import net.minecraft.commands.SharedSuggestionProvider;

/**
 * {@code .zh} — re-apply the translation and report dictionary statistics.
 */
public class ZhCommand extends Command {
    public ZhCommand() {
        super("zh", "Meteor-zh translation control.");
    }

    @Override
    public void build(LiteralArgumentBuilder<SharedSuggestionProvider> builder) {
        builder.executes(context -> {
            int count = Translator.translateAll();
            info("已重新翻译 %d 处文本（词典 %d 条）", count, ZhDict.size());
            return SINGLE_SUCCESS;
        });

        builder.then(literal("reload").executes(context -> {
            ZhDict.load();
            Translator.init();
            int count = Translator.translateAll();
            info("词典重新加载完成，翻译 %d 处文本", count);
            return SINGLE_SUCCESS;
        }));

        builder.then(literal("info").executes(context -> {
            info("Meteor-zh 词典条目：%d", ZhDict.size());
            return SINGLE_SUCCESS;
        }));
    }
}
