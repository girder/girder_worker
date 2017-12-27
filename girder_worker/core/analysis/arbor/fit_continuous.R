#data(anolis); tree <- anolis$phy; table <- anolis$dat; column <- "PCI_limbs"; model="EB"

## fitContinuous script
library(aRbor)
library(geiger)
library(cardoonTools)

td <- make.treedata(tree, table)
td <- checkNumeric(td)
valid.numeric <- which(colnames(td$dat)==column)
if(length(valid.numeric)==0){
  stop("The supplied column is not present, or is not a valid continuous trait")
}
td <- select(td, valid.numeric)

o <- fitContinuous(td$phy, td$dat, model=model, SE=0)
opt = o$opt

if (model == "OU") {
  fit=list(z0=opt$z0, sigsq=opt$sigsq, alpha=opt$alpha, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
  result<-rescale(tree, "OU", o$opt$alpha)
} else if (model == "BM") {
  fit=list(z0=opt$z0, sigsq=opt$sigsq, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
  result<-tree
} else if (model == "EB") {
  fit=list(z0=opt$z0, sigsq=opt$sigsq, a=opt$a, lnL=opt$lnL, AIC=opt$aic, AICc=opt$aicc)
  result<-rescale(tree, "EB", o$opt$a)
}

treePlot = cardoonPlot(expression(plotContrasts(td$phy, setNames(td$dat[,1], td$phy$tip.label), cex.tip.label=0.5)), width=1000, height=1000, res=100)
treePlot = treePlot$png
