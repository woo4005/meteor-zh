/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
package com.meteorzh.mixin;

import baritone.api.utils.Helper;
import com.meteorzh.ChatDict;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Baritone 的聊天提示汉化。
 *
 * <p>为什么不去拦 Meteor 那套 {@code ChatUtils}：Baritone 不走它。Baritone 自己有一层
 * 日志封装 {@code baritone.api.utils.Helper}，里面一串 {@code logDirect} 重载，
 * 最终都汇到 {@code logDirect(boolean, Component...)} —— 由它拼上
 * {@code [Baritone] } 前缀再丢进聊天栏。
 *
 * <p>所以这里直接改这个汇聚点的 {@code Component[]} 参数：每个元素取纯文本查词典，
 * 命中就用译文重建 {@code Component}（保留原样式），未命中原样放行。
 *
 * <p>三个设计取舍：
 * <ul>
 *   <li>{@code remap = false}：目标类 {@code Helper} 与目标方法 {@code logDirect} 都是
 *       Baritone 的，不是 Minecraft 的，不能被我们的 remap 映射表处理。</li>
 *   <li>{@code method = "logDirect"} 不带描述符：{@code logDirect} 有 7 个重载，
 *       带描述符就要写 {@code ChatFormatting} 的 intermediary 名（{@code class_124}），
 *       两条版本线不一定一致。不写描述符则由 Mixin 自己按参数类型挑。</li>
 *   <li>{@code require = 0}：Baritone 换了实现（比如哪天又改回 {@code BaritoneChatControl}）
 *       时，我们宁可不翻译，也不能让游戏因为注入失败而起不来。</li>
 * </ul>
 *
 * <p>另外 {@code ChatFormatting} 为 {@code RED} 的错误消息也走这条路径，所以错误提示
 * 同样会被翻译；{@code logNotification} / {@code logDebug} 也经 {@code logDirect} 落地。
 */
@Mixin(value = Helper.class, remap = false)
public abstract class BaritoneHelperMixin {
    @ModifyVariable(method = "logDirect", at = @At("HEAD"), argsOnly = true,
                    ordinal = 0, require = 0, remap = false)
    private static Component[] meteorzh$translateDirect(Component[] components) {
        if (components == null || components.length == 0) {
            return components;
        }

        Component[] out = null;
        for (int i = 0; i < components.length; i++) {
            Component original = components[i];
            if (original == null) {
                continue;
            }

            String text = original.getString();
            if (text == null || text.isEmpty()) {
                continue;
            }

            String zh = ChatDict.translate(text);
            if (zh == null || zh.equals(text)) {
                continue;
            }

            if (out == null) {
                out = components.clone();
            }
            out[i] = Component.literal(zh).withStyle(original.getStyle());
        }

        return out == null ? components : out;
    }
}
