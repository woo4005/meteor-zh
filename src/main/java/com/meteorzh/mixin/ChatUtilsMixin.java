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

import com.meteorzh.ChatDict;
import meteordevelopment.meteorclient.utils.player.ChatUtils;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * 聊天栏消息正文的翻译。
 *
 * <p>挂在 {@code ChatUtils.formatMsg(String, ChatFormatting)} 上 —— 它是所有带文本
 * 消息的唯一汇聚点（{@code info/warning/error}、{@code sendMsg(...)} 的 7 个重载、
 * {@code formatCoords} 最后都会走到这里），而且是 private static，名字在
 * Meteor 1.21.11 与 26.1 两个版本里都唯一。
 *
 * <p>选它而不是 {@code info/warning/error} 的原因：Jefff 的仓库寻找器、Meteor 的
 * Notifier 这类 addon 直接调 {@code ChatUtils.sendMsg(int, ChatFormatting, String, Object...)}，
 * 根本不经过 info。
 *
 * <p>选它而不是 {@code sendMsg} 的原因：{@code sendMsg} 有 7 个重载，注解里必须
 * 带描述符才能唯一定位，而描述符里含 {@code ChatFormatting} —— 两条线的类名不同
 * （1.21.11 混淆成 {@code class_124}、26.1 就是 {@code ChatFormatting}），一份源码
 * 写不出两边都能用的描述符。{@code formatMsg} 只写方法名即可，注解里不含任何
 * MC 类型，所以 {@code remap = false} 在两条线上都成立。
 *
 * <p>注意：到达 {@code formatMsg} 时 {@code %s} 已经被 {@code String.format} 填掉了，
 * 所以翻译走的是 {@link ChatDict} 的「模板反查」而不是精确查表。
 */
@Mixin(value = ChatUtils.class, remap = false)
public class ChatUtilsMixin {
    @ModifyVariable(method = "formatMsg", at = @At("HEAD"), argsOnly = true, ordinal = 0, remap = false)
    private static String meteorzh$formatMsg(String message) {
        String zh = ChatDict.translate(message);
        return zh != null ? zh : message;
    }
}
