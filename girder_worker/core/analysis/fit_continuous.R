library(geiger)

data <- table[,column]
names(data) <- table[,1]
o <- fitContinuous(tree, data, model=model, SE=0)
opt = o$opt

if (model == "OU") {
    fit=list("value", z0=opt$z0, sigsq=opt$sigsq, alpha=opt$alpha, " "=" ", lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    # result<-transform(tree, "OU", o$opt$alpha)
    result<-tree
} else if (model == "BM") {
    fit=list("value", z0=opt$z0, sigsq=opt$sigsq, " "=" ", lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    result<-tree
} else if (model == "EB") {
    fit=list("value",z0=opt$z0, sigsq=opt$sigsq, a=opt$a, " "=" ", lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
    # result<-transform(tree, "EB", o$opt$a)
    result<-tree
}
