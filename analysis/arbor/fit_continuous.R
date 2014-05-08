library(geiger)
library(cardoonTools)

data <- table[,column]
names(data) <- row.names(table)
o <- fitContinuous(tree, data, model=model, SE=0)
opt = o$opt

if (model == "OU") {
    fit=list(z0=opt$z0, sigsq=opt$sigsq, alpha=opt$alpha, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    result<-transform(tree, "OU", o$opt$alpha)
} else if (model == "BM") {
    fit=list(z0=opt$z0, sigsq=opt$sigsq, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    result<-tree
} else if (model == "EB") {
    fit=list(z0=opt$z0, sigsq=opt$sigsq, a=opt$a, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    result<-transform(tree, "EB", o$opt$a)
}

treePlot = cardoonPlot(expression(plot(result, cex=0.5)), width=1000, height=1000, res=100)
treePlot = treePlot$png
