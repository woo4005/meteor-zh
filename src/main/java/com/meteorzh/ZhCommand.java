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

/**
 * {@code .zh} — re-apply the translation, reload the dictionary, report state.
 *
 * <p>注意这里故意写成原始类型 {@code LiteralArgumentBuilder}（不带泛型参数）：
 * Meteor 1.21.11 的 {@code Command.build} 参数是
 * {@code LiteralArgumentBuilder<SharedSuggestionProvider>}，而 26.1 起改成了
 * {@code LiteralArgumentBuilder<ClientSuggestionProvider>}。泛型擦除后签名相同，
 * 原始类型正好能同时覆盖两边的抽象方法，一份源码即可编译两个游戏版本。
 */
public class ZhCommand extends Command {
    public ZhCommand() {
        super("zh", "Meteor-zh translation control.");
    }

    @Override
    @SuppressWarnings("rawtypes")
    public void build(LiteralArgumentBuilder builder) {
        builder.executes(context -> {
            int count = Translator.translateAll();
            info("已重新翻译 %d 处文本（词典 %d 条）", count, ZhDict.size());
            return SINGLE_SUCCESS;
        });

        builder.then(literal("reload").executes(context -> {
            // ZhDict.load() is a no-op once loaded, so this has to be reload().
            ZhDict.reload();
            Translator.init();
            int count = Translator.translateAll();
            info("词典已重新加载：%d 条，重新翻译 %d 处文本", ZhDict.size(), count);
            return SINGLE_SUCCESS;
        }));

        builder.then(literal("info").executes(context -> {
            info("词典 %d 条，词表 %d 条", ZhDict.size(), WordTranslator.size());
            info("字体：%s", FontFixer.describe());
            info("界面文本渲染器：%s", FontFixer.usingVanilla()
                ? "Minecraft 原版（可显示中文）"
                : "Meteor 自带图集（只有拉丁/希腊/西里尔，中文会变成空白）");
            return SINGLE_SUCCESS;
        }));

        builder.then(literal("font").executes(context -> {
            boolean changed = FontFixer.ensureVanillaRenderer();
            if (changed) {
                info("已关闭 Meteor 自定义字体，改用 Minecraft 原版字体 —— 中文现在可以显示了");
            } else if (FontFixer.usingVanilla()) {
                info("当前已经在使用 Minecraft 原版字体（可显示中文），无需修改");
            } else {
                warning("无法切换到原版字体渲染器，请在 Meteor 设置 > Visual 里关闭 Custom Font");
            }
            return SINGLE_SUCCESS;
        }));
    }
}
