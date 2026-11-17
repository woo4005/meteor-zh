/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
package com.meteorzh;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.client.gui.components.toasts.ToastManager;
import net.minecraft.network.chat.Component;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * 跨版本兼容层。
 *
 * <p>Minecraft 26.2 把 {@code Minecraft#getToastManager()} 移到了 {@code Minecraft#gui} 上的
 * {@code Gui#toastManager()}；26.1 及更早版本只有前者。这里用反射同时支持两版，
 * 这样同一份源码在两条构建线（1.x / 2.x）上都不需要条件编译，也不会因为
 * 编译基线不同而互相 NoSuchMethodError。
 *
 * <p>只做「取不到就降级」而不是抛异常：更新提示属于可选功能，拿不到 ToastManager
 * 时宁可静默，也不该让主流程炸掉。
 */
public final class Compat {
    private Compat() {
    }

    /** 取 ToastManager；两个版本都没有时返回 null，由调用方决定怎么降级。 */
    public static ToastManager toastManager() {
        Minecraft mc = Minecraft.getInstance();
        if (mc == null) return null;

        // 26.2+ ：Minecraft.gui.toastManager()
        try {
            Field guiField = Minecraft.class.getField("gui");
            Object gui = guiField.get(mc);
            if (gui != null) {
                Method m = gui.getClass().getMethod("toastManager");
                Object tm = m.invoke(gui);
                if (tm instanceof ToastManager manager) {
                    return manager;
                }
            }
        } catch (Throwable ignored) {
            // 版本不匹配是预期路径之一，静默跳到下一分支。
        }

        // 26.1 及更早 ：Minecraft#getToastManager()
        try {
            Method m = Minecraft.class.getMethod("getToastManager");
            Object tm = m.invoke(mc);
            if (tm instanceof ToastManager manager) {
                return manager;
            }
        } catch (Throwable ignored) {
            // 同上。
        }

        return null;
    }

    /** 弹一个系统提示；拿不到 ToastManager 时静默放弃。 */
    public static void toast(SystemToast.SystemToastId id, String title, String subtitle) {
        if (id == null) return;
        ToastManager tm = toastManager();
        if (tm == null) return;
        SystemToast.add(tm, id, Component.literal(title), Component.literal(subtitle));
    }
}
