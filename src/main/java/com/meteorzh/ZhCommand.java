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
