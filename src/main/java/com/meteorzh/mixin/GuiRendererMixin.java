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
