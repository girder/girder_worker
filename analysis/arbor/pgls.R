require(ape)
require(nlme)
require(cardoonTools)

if(correlation=="BM"){
  cor <- corBrownian(1, phy=tree)
}
if(correlation=="OU"){
  cor <- corMartins(1, phy=tree, fixed=FALSE)
}
if(correlation=="Pagel"){
  cor <- corPagel(1, phy=tree, fixed=FALSE)
  cor1 <- corPagel(1, phy=tree, fixed=TRUE)
  cor0 <- corPagel(0, phy=tree, fixed=TRUE)
}
if(correlation=="ACDC"){
  cor <- corBlomberg(1, phy=tree, fixed=FALSE)
}

fmla <- as.formula(paste(as.character(dep_variable), "~", as.character(ind_variable),sep=""))
res <- gls(model=fmla, correlation=cor, data=table)
sum_res <- summary(res)
coefficients <- sum_res$tTable
modelfit_summary <- data.frame("AIC"= sum_res$AIC, loglik=sum_res$logLik, residual_SE=sum_res$sigma, df_total=sum_res$dims$N, df_residual=sum_res$dims$N-sum_res$dims$p)

pgls_plot <- function() {
  plot(table[,ind_variable], table[,dep_variable], pch=21, bg="gray80", xlab=ind_variable, ylab=dep_variable)
  abline(res, lty=2, lwd=2)
}

pglsPlot = cardoonPlot(expression(pgls_plot()), width=1000, height=1000, res=100)
pglsPlot = pglsPlot$png
